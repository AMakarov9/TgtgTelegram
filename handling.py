from datetime import datetime
import pytz

# Quick GPT generated
def convert_and_format_time(datetime_str: str, local_timezone='Europe/Oslo') -> str:
    utc_zone = pytz.utc

    utc_time = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
    
    utc_time = utc_zone.localize(utc_time)
    
    local_time = utc_time.astimezone(pytz.timezone(local_timezone))
    formatted_time = local_time.strftime("%Y-%m-%dT%H:%M:%S%z")
    
    return formatted_time

# print(convert_and_format_time('2024-07-02T14:45:00Z'))

