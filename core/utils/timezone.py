from datetime import datetime
import os
from typing import Optional
from zoneinfo import ZoneInfo

def get_timezone() -> str:
    """Get timezone from environment variable or use default.
    
    Returns:
        str: Timezone string (e.g. 'Asia/Shanghai')
    """
    return os.getenv('TZ', 'UTC')

def get_formatted_date(timezone: Optional[str] = None) -> str:
    """Get formatted date string with timezone awareness.
    
    Args:
        timezone: Optional timezone string. If not provided, uses TZ from env or UTC.
        
    Returns:
        str: Formatted date string (e.g. 'Today's Date: Mon, Jan 01, 2024')
    """
    tz = ZoneInfo(timezone or get_timezone())
    now = datetime.now(tz)
    return f"Today's Date: {now.strftime('%a, %b %d, %Y')}"

def get_current_time(timezone: Optional[str] = None) -> datetime:
    """Get current time with timezone awareness.
    
    Args:
        timezone: Optional timezone string. If not provided, uses TZ from env or UTC.
        
    Returns:
        datetime: Current time with timezone information
    """
    tz = ZoneInfo(timezone or get_timezone())
    return datetime.now(tz)