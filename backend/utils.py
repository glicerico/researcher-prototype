"""
Utility functions used across the application.
"""
import time

def get_current_datetime_str() -> str:
    """Return the current date and time as a formatted string."""
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime()) 