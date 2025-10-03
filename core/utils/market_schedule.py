import holidays
from datetime import datetime, time
import os
import logging

logger = logging.getLogger(__name__)

def is_market_open_time(check_force=True) -> bool:
    """
    Checks if the Korean stock market is currently open.
    - Not a weekend (Sat, Sun)
    - Not a South Korean public holiday
    - Not the last day of the year (Dec 31)
    - Between 09:00 and 15:30
    
    :param check_force: If True, checks for FORCE_RUN_MARKET_CLOSED env var to override.
    :return: True if market is open (or forced), False otherwise.
    """
    if check_force:
        force_run = os.getenv("FORCE_RUN_MARKET_CLOSED", "false").lower() == "true"
        if force_run:
            logger.warning("Market check skipped due to FORCE_RUN_MARKET_CLOSED=true")
            return True

    now = datetime.now()
    
    # 1. Check Weekend (Sat=5, Sun=6)
    if now.weekday() >= 5:
        logger.info(f"Market is closed today ({now.strftime('%Y-%m-%d')}) - Weekend.")
        return False

    # 2. Check South Korean Public Holidays
    kr_holidays = holidays.KR()
    if now in kr_holidays:
        logger.info(f"Market is closed today ({now.strftime('%Y-%m-%d')}) - Holiday: {kr_holidays.get(now)}")
        return False

    # 3. Check for last business day of the year (Dec 31)
    if now.month == 12 and now.day == 31:
        logger.info(f"Market is closed today ({now.strftime('%Y-%m-%d')}) - Year-end closing day.")
        return False

    # 4. Check operational hours (09:00 ~ 15:30)
    current_time = now.time()
    start_time = time(9, 0)
    end_time = time(15, 30)

    if start_time <= current_time <= end_time:
        return True
    else:
        logger.info(f"Market is closed (Current time: {current_time}). Trading hours are 09:00 - 15:30.")
        return False
