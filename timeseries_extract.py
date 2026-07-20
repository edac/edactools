"""Pull a per-band value out of a 3D raster for a point or an area.

A point takes the pixel it lands in; an area averages every valid pixel whose
cell the shape covers. Both walk the bands in order, so band N of the result
lines up with band N of the raster and therefore with the date the caller
derives from :mod:`band_dates`.

Like the index tools, this reads through GDAL and never pulls a whole band into
memory: only the window the shape covers is read, and that window is walked in
horizontal strips, so sampling a small area out of a huge raster stays cheap.
"""

import math

import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import QgsCoordinateTransform, QgsGeometry, QgsProject, QgsWkbTypes

# A window bigger than this would need a mask array too large to be worth
# allocating; the user is asked to draw something smaller instead.
_MAX_WINDOW_PIXELS = 50_000_000

_STRIP_ROWS = 512


class ExtractError(RuntimeError):
    """Raised with a message meant to be shown to the user."""


def _to_layer_crs(geometry, geometry_crs, layer):
    """Reproject ``geometry`` into ``layer``'s CRS."""
    geom = QgsGeometry(geometry)
    if geometry_crs != layer.crs():
        transform = QgsCoordinateTransform(geometry_crs, layer.crs(), QgsProject.instance())
        if geom.transform(transform) != 0:
            raise ExtractError("Could not reproject the sample area to %s." % layer.name())
    return geom


def _open(layer):
    dataset = gdal.Open(layer.source())
    if dataset is None:
        raise ExtractError(
            "Could not read '%s' with GDAL. This tool needs a raster stored as a "
            "file (for example a GeoTIFF)." % layer.name())
    return dataset


def _window_for(dataset, geom):
    """Pixel window (xoff, yoff, width, height) covering ``geom``'s extent."""
    gt = dataset.GetGeoTransform()
    inverse = gdal.InvGeoTransform(gt)
    if inverse is None:
        raise ExtractError("Raster has a geotransform that cannot be inverted.")
    box = geom.boundingBox()
    corners = [(box.xMinimum(), box.yMinimum()), (box.xMaximum(), box.yMinimum()),
               (box.xMinimum(), box.yMaximum()), (box.xMaximum(), box.yMaximum())]
    pixels = [gdal.ApplyGeoTransform(inverse, x, y) for x, y in corners]
    cols = [p[0] for p in pixels]
    rows = [p[1] for p in pixels]
    x0 = max(0, int(math.floor(min(cols))))
    y0 = max(0, int(math.floor(min(rows))))
    x1 = min(dataset.RasterXSize, int(math.ceil(max(cols))))
    y1 = min(dataset.RasterYSize, int(math.ceil(max(rows))))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1 - x0, y1 - y0


def _polygon_mask(dataset, geom, window):
    """Rasterise ``geom`` over ``window``, returning a bool array (h, w).

    ALL_TOUCHED is on so an area smaller than a pixel still selects the pixel it
    sits in rather than silently averaging nothing.
    """
    xoff, yoff, width, height = window
    gt = dataset.GetGeoTransform()
    origin_x, origin_y = gdal.ApplyGeoTransform(gt, xoff, yoff)
    window_gt = (origin_x, gt[1], gt[2], origin_y, gt[4], gt[5])

    source = ogr.GetDriverByName("Memory").CreateDataSource("mask")
    # The geometry is already in the raster's CRS, so declaring the same CRS on
    # the mask layer makes the burn a no-op transform. Leaving it unset instead
    # makes GDAL log a "failed to fetch spatial reference" warning every call.
    srs = None
    projection = dataset.GetProjection()
    if projection:
        srs = osr.SpatialReference()
        srs.ImportFromWkt(projection)
    # wkbUnknown, not wkbPolygon: several selected features union into a
    # multipolygon, and the mask must burn that just as happily.
    layer = source.CreateLayer("shape", srs=srs, geom_type=ogr.wkbUnknown)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(ogr.CreateGeometryFromWkt(geom.asWkt()))
    layer.CreateFeature(feature)

    target = gdal.GetDriverByName("MEM").Create("", width, height, 1, gdal.GDT_Byte)
    target.SetGeoTransform(window_gt)
    gdal.RasterizeLayer(target, [1], layer, burn_values=[1],
                        options=["ALL_TOUCHED=TRUE"])
    mask = target.GetRasterBand(1).ReadAsArray().astype(bool)
    return mask


def _valid(values, nodata):
    good = np.isfinite(values)
    if nodata is not None and math.isfinite(nodata):
        good &= ~np.isclose(values, nodata)
    return good


def _band_mean(band, window, mask):
    """Mean of the masked, valid pixels of ``band`` within ``window``."""
    xoff, yoff, width, height = window
    total = 0.0
    count = 0
    for y in range(0, height, _STRIP_ROWS):
        rows = min(_STRIP_ROWS, height - y)
        strip = band.ReadAsArray(xoff, yoff + y, width, rows)
        if strip is None:
            continue
        strip = strip.astype(np.float64)
        good = mask[y:y + rows] & _valid(strip, band.GetNoDataValue())
        if good.any():
            total += float(strip[good].sum())
            count += int(good.sum())
    return total / count if count else None


def _point_values(dataset, geom):
    """Every band's value at the pixel under ``geom``."""
    gt = dataset.GetGeoTransform()
    inverse = gdal.InvGeoTransform(gt)
    point = geom.asPoint()
    col, row = gdal.ApplyGeoTransform(inverse, point.x(), point.y())
    col, row = int(math.floor(col)), int(math.floor(row))
    if not (0 <= col < dataset.RasterXSize and 0 <= row < dataset.RasterYSize):
        return None
    values = []
    for index in range(1, dataset.RasterCount + 1):
        band = dataset.GetRasterBand(index)
        cell = band.ReadAsArray(col, row, 1, 1)
        if cell is None:
            values.append(None)
            continue
        cell = cell.astype(np.float64)
        values.append(float(cell[0, 0]) if _valid(cell, band.GetNoDataValue())[0, 0] else None)
    return values


def extract_series(layer, geometry, geometry_crs, progress=None):
    """Return one value per band of ``layer`` under ``geometry``.

    ``geometry`` is a point or polygon in ``geometry_crs``. The result is a list
    of floats and Nones (None where the pixel was nodata or the shape missed the
    raster) with one entry per band, or None if ``progress`` cancelled the run.

    ``progress`` is called as ``progress(done, total)`` and returns False to
    cancel.
    """
    geom = _to_layer_crs(geometry, geometry_crs, layer)
    dataset = _open(layer)
    try:
        bands = dataset.RasterCount
        if geom.type() == QgsWkbTypes.PointGeometry:
            values = _point_values(dataset, geom)
            if progress:
                progress(bands, bands)
            return values if values is not None else [None] * bands

        window = _window_for(dataset, geom)
        if window is None:
            return [None] * bands
        if window[2] * window[3] > _MAX_WINDOW_PIXELS:
            raise ExtractError(
                "That area covers %d pixels of '%s', which is too large to average. "
                "Draw a smaller area." % (window[2] * window[3], layer.name()))

        mask = _polygon_mask(dataset, geom, window)
        if not mask.any():
            return [None] * bands

        values = []
        for index in range(1, bands + 1):
            values.append(_band_mean(dataset.GetRasterBand(index), window, mask))
            if progress and not progress(index, bands):
                return None
        return values
    finally:
        dataset = None
