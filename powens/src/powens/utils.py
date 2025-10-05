"""
Utils for the powens package
"""

from datetime import datetime as dt
import dateutil.parser as dateutil_parser

def parse_optional_date(date: str | None) -> dt | None:
    content_date = date
    if content_date is None:
        return None
    return dateutil_parser.parse(date)
