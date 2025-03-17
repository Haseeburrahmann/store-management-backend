"""
DateTime Handler module for consistent date and time handling throughout the application.
"""
from datetime import datetime, date, time, timedelta
from typing import Union, Optional, Tuple
import re


class DateTimeHandler:
    """
    Centralized service for handling dates and times consistently throughout the application.
    Provides methods for parsing, formatting, and common date operations.
    """

    # Standard format strings
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M"
    DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

    @classmethod
    def parse_date(cls, date_str: str) -> Optional[date]:
        """
        Parse a date string in YYYY-MM-DD format to a date object.

        Args:
            date_str: String in YYYY-MM-DD format

        Returns:
            Date object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            # Validate format with regex
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                print(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
                return None

            return datetime.strptime(date_str, cls.DATE_FORMAT).date()
        except Exception as e:
            print(f"Error parsing date {date_str}: {str(e)}")
            return None

    @classmethod
    def format_date(cls, date_obj: Union[date, datetime, None]) -> Optional[str]:
        """
        Format a date/datetime object to YYYY-MM-DD string.

        Args:
            date_obj: Date or datetime object

        Returns:
            Formatted date string or None
        """
        if date_obj is None:
            return None

        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()

        return date_obj.strftime(cls.DATE_FORMAT)

    @classmethod
    def parse_time(cls, time_str: str) -> Optional[time]:
        """
        Parse a time string in HH:MM format to a time object.

        Args:
            time_str: String in HH:MM format

        Returns:
            Time object or None if parsing fails
        """
        if not time_str:
            return None

        try:
            # Validate format with regex
            if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_str):
                print(f"Invalid time format: {time_str}. Expected HH:MM (24-hour)")
                return None

            return datetime.strptime(time_str, cls.TIME_FORMAT).time()
        except Exception as e:
            print(f"Error parsing time {time_str}: {str(e)}")
            return None

    @classmethod
    def format_time(cls, time_obj: Union[time, datetime, None]) -> Optional[str]:
        """
        Format a time/datetime object to HH:MM string.

        Args:
            time_obj: Time or datetime object

        Returns:
            Formatted time string or None
        """
        if time_obj is None:
            return None

        if isinstance(time_obj, datetime):
            time_obj = time_obj.time()

        return time_obj.strftime(cls.TIME_FORMAT)

    @classmethod
    def get_current_datetime(cls) -> datetime:
        """
        Get the current UTC datetime.

        Returns:
            Current UTC datetime
        """
        return datetime.utcnow()

    @classmethod
    def get_current_date(cls) -> date:
        """
        Get the current UTC date.

        Returns:
            Current UTC date
        """
        return datetime.utcnow().date()

    @classmethod
    def get_week_boundaries(cls, reference_date: Union[date, datetime, str, None] = None) -> Tuple[date, date]:
        """
        Get the start (Monday) and end (Sunday) dates of the week containing the reference date.
        If no reference date is provided, uses the current date.

        Args:
            reference_date: Date within the desired week

        Returns:
            Tuple of (week_start_date, week_end_date)
        """
        if reference_date is None:
            reference_date = cls.get_current_date()

        if isinstance(reference_date, str):
            reference_date = cls.parse_date(reference_date)
            if reference_date is None:
                reference_date = cls.get_current_date()

        if isinstance(reference_date, datetime):
            reference_date = reference_date.date()

        # Calculate Monday (start of week)
        days_since_monday = reference_date.weekday()  # Monday is 0, Sunday is 6
        week_start = reference_date - timedelta(days=days_since_monday)
        # Calculate Sunday (end of week)
        week_end = week_start + timedelta(days=6)

        return week_start, week_end

    @classmethod
    def date_to_datetime(cls, date_obj: date, set_to_end_of_day: bool = False) -> datetime:
        """
        Convert a date object to a datetime object.

        Args:
            date_obj: Date to convert
            set_to_end_of_day: If True, sets time to 23:59:59, otherwise 00:00:00

        Returns:
            Datetime object
        """
        if set_to_end_of_day:
            return datetime.combine(date_obj, time(23, 59, 59))
        return datetime.combine(date_obj, time.min)

    @classmethod
    def is_future_date(cls, date_obj: Union[date, datetime]) -> bool:
        """
        Check if a date is in the future.

        Args:
            date_obj: Date to check

        Returns:
            True if date is in the future
        """
        if isinstance(date_obj, datetime):
            return date_obj > cls.get_current_datetime()
        return date_obj > cls.get_current_date()

    @classmethod
    def is_past_date(cls, date_obj: Union[date, datetime]) -> bool:
        """
        Check if a date is in the past.

        Args:
            date_obj: Date to check

        Returns:
            True if date is in the past
        """
        if isinstance(date_obj, datetime):
            return date_obj < cls.get_current_datetime()
        return date_obj < cls.get_current_date()