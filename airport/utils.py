import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from rest_framework.exceptions import ValidationError


def params_to_ints(query_params, name):
    """
    Parse integer query parameters into a list of ints.

    Accepts both repeated (?ids=1&ids=2) and comma-separated (?ids=1,2,3) formats.

    Raises:
        ValidationError: if any value cannot be converted to int.
    """
    raw = query_params.getlist(name)
    if not raw:
        return []

    pieces = [
        str_id.strip()
        for item in raw
        for str_id in item.split(",")
        if str_id.strip()
    ]

    ints = []
    for p in pieces:
        if not p.isdigit():
            raise ValidationError({name: [f"'{p}' is not a valid integer"]})
        ints.append(int(p))

    return ints

def params_to_str(query_params, name, max_length=0, alpha=True, upper=False, choices=None):
    """
    Parse and validate string-based query parameters.

    Args:
        query_params: request.query_params.
        name: parameter name.
        max_length: enforce exact length if > 0.
        alpha: if True, restrict to alphabetic chars.
        upper: if True, convert values to uppercase.
        choices: optional iterable of allowed values (case-insensitive).

    Returns:
        A list of validated strings.
    """
    raw = query_params.getlist(name)
    if not raw:
        return []

    pieces = [
        value.strip()
        for item in raw
        for value in item.split(",")
        if value.strip()
    ]

    values = []
    for p in pieces:
        if alpha:
            if not p.isalpha():
                raise ValidationError({name: [f"'{p}' must contain only alphabetic characters"]})

        if max_length > 0:
            if not len(p) == max_length:
                raise ValidationError({name: [f"'{p}' is not exactly {max_length} letters"]})

        if choices:
            if p.lower() not in [c.lower() for c in choices]:
                raise ValidationError({name: [f"'{p}' is not a valid value for {name}"]})

        if upper:
            values.append(p.upper())
        else:
            values.append(p)

    return values

def params_to_datetime(query_params, name):
    """
    Parse a single datetime parameter in '%Y-%m-%d %H:%M' format
    and return a timezone-aware UTC datetime.

    Example: ?departure_time=2025-11-07 10:30

    Raises:
        ValidationError: if the format is invalid.
    """
    query_str = query_params.get(name)
    if not query_str:
        return None

    date_format = "%Y-%m-%d %H:%M"

    try:
        date_time = datetime.datetime.strptime(query_str, date_format)
    except ValueError:
        raise ValidationError({name: [f"invalid date format, please use {date_format}"]})

    date_time = timezone.make_aware(date_time, datetime.timezone.utc)

    return date_time

def parse_date_range(date_str, name, time_zone=None):
    """
    Convert a 'YYYY-MM-DD' string into a (start, end) tuple of aware datetimes.

    The start corresponds to midnight of that date in the given timezone,
    converted to an aware datetime. The end is exactly 24 hours later.

    Args:
        date_str: the input date string.
        name: parameter name (for error reporting).
        time_zone: optional IANA timezone string (e.g. 'Europe/Warsaw').

    Returns:
        (start_datetime, end_datetime), both timezone-aware.

    Raises:
        ValidationError: on invalid date format or invalid timezone name.
    """
    if not date_str:
        return None

    date_format = "%Y-%m-%d"
    try:
        date_time = datetime.datetime.strptime(date_str, date_format)
    except ValueError:
        raise ValidationError({name: [f"invalid date format, please use {date_format}"]})

    if timezone.is_naive(date_time):
        if time_zone is not None:
            try:
                time_zone = ZoneInfo(time_zone)
            except ZoneInfoNotFoundError:
                raise ValidationError({"time_zone": [f"timezone must be a valid IANA string, e.g. 'America/New_York'."]})
            date_time = timezone.make_aware(date_time, time_zone)
        else:
            date_time = timezone.make_aware(date_time, datetime.timezone.utc)

    date_time = (
        date_time,
        date_time + datetime.timedelta(days=1)
    )

    return date_time

def params_to_decimal(query_params, name):
    """
    Parse a decimal query parameter.

    Returns:
        Decimal or None
    Raises:
        ValidationError: when the value is not a valid decimal string.
    """
    query_str = query_params.get(name)
    if not query_str:
        return None

    try:
        return Decimal(query_str)
    except (InvalidOperation, ValueError):
        raise ValidationError({name: [f"{query_str} is not a valid decimal"]})
