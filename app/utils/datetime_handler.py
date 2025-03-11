# Add this to utils/formatting.py or create a new file utils/datetime_handler.py
import re
from datetime import datetime, timezone
from typing import Optional, Union


class DateTimeHandler:
    """
    Centralized service for handling date and time operations consistently across the application.
    """

    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """
        Parse a date string in YYYY-MM-DD format to a datetime object.
        Returns None if parsing fails.
        """
        try:
            if not date_str:
                return None

            # Check format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                print(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
                return None

            return datetime.strptime(date_str, "%Y-%m-%d")
        except Exception as e:
            print(f"Error parsing date: {str(e)}")
            return None

    @staticmethod
    def parse_time(time_str: str) -> Optional[str]:
        """
        Validate a time string in HH:MM format.
        Returns the validated time string or None if validation fails.
        """
        try:
            if not time_str:
                return None

            # Check format
            if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_str):
                print(f"Invalid time format: {time_str}. Expected HH:MM (24-hour)")
                return None

            return time_str
        except Exception as e:
            print(f"Error parsing time: {str(e)}")
            return None

    @staticmethod
    def normalize_datetime(dt: Optional[Union[datetime, str]]) -> Optional[datetime]:
        """
        Normalize a datetime object or string to a naive UTC datetime.
        Returns None if conversion fails.
        """
        try:
            if not dt:
                return None

            # Convert string to datetime if needed
            if isinstance(dt, str):
                try:
                    # Try ISO format first
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        # Try common format
                        dt = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        print(f"Invalid datetime format: {dt}")
                        return None

            # Remove timezone info if present
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)

            return dt
        except Exception as e:
            print(f"Error normalizing datetime: {str(e)}")
            return None

    @staticmethod
    def format_datetime(dt: Optional[datetime]) -> Optional[str]:
        """
        Format a datetime object to ISO format for consistent API responses.
        Returns None if formatting fails.
        """
        try:
            if not dt:
                return None

            return dt.isoformat()
        except Exception as e:
            print(f"Error formatting datetime: {str(e)}")
            return None

    @staticmethod
    def get_current_datetime() -> datetime:
        """
        Get the current UTC datetime as a naive datetime object.
        """
        return datetime.utcnow()

    @staticmethod
    def is_valid_range(start_dt: Optional[datetime], end_dt: Optional[datetime]) -> bool:
        """
        Validate that the end datetime is after the start datetime.
        """
        if not start_dt or not end_dt:
            return False

        return end_dt > start_dt