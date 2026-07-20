"""Shared band-to-date mapping for the raster time tools.

Flipper and Time Series both label the bands of a 3D raster with acquisition
dates the same way: band 1 is the start date and every band after it advances
by one step, so a stack of 16-day composites uses a step of 16 days and a
monthly stack uses 1 month. Keeping the mapping in one place stops the two
tools from drifting apart.
"""

# Order matters: this is the order the unit combo boxes are populated in.
INTERVAL_UNITS = ("days", "weeks", "months", "years")


def date_for_band(start, band, step, unit):
    """Return the QDate of 1-based ``band``, counting from the ``start`` QDate.

    ``step`` is the number of ``unit``s between consecutive bands. Each date is
    measured from ``start`` rather than from the previous band, so month steps
    land on the calendar day rather than drifting: starting Jan 31 with a
    1-month step gives Jan 31, Feb 28, Mar 31 (QDate clamps short months).
    """
    steps = step * (band - 1)
    if unit == "days":
        return start.addDays(steps)
    if unit == "weeks":
        return start.addDays(steps * 7)
    if unit == "months":
        return start.addMonths(steps)
    if unit == "years":
        return start.addYears(steps)
    raise ValueError("unknown interval unit: %s" % unit)
