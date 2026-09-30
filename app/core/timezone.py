from datetime import date, datetime, time, timedelta, timezone

# The JAC operates in Medellín, Colombia (America/Bogotá, UTC-5, no DST).
# "A full day" for date-range filters (RNG-22: reports, and audit search)
# means a full local business day, not a full UTC day — anchoring to UTC
# directly would misclassify events near the UTC day boundary (e.g. 7pm-
# midnight local time is already "tomorrow" in UTC).
BUSINESS_TIMEZONE = timezone(timedelta(hours=-5))


def day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """Returns the (start, end) UTC instants covering the full local day."""
    start_local = datetime.combine(day, time.min, tzinfo=BUSINESS_TIMEZONE)
    end_local = datetime.combine(day, time.max, tzinfo=BUSINESS_TIMEZONE)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
