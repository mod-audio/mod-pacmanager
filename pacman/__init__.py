import datetime

def json_handler(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return None

