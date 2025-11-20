import redis.asyncio as redis
import os
import datetime
import json
from typing import Optional, Any, Dict

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

redis_client = None

async def init_redis():
    global redis_client
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        redis_client = client
    except Exception:
        redis_client = None

def orm_to_dict(obj):
    result = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, (datetime.date, datetime.datetime)):
            result[column.name] = value.isoformat()
        else:
            result[column.name] = value
    return result

def dict_to_orm(model_class, data: dict):
    for column in model_class.__table__.columns:
        colname = column.name
        if colname in data:
            try:
                py_type = getattr(column.type, 'python_type', None)
            except AttributeError:
                py_type = None

            if py_type in [datetime.date, datetime.datetime]:
                try:
                    data[colname] = datetime.datetime.fromisoformat(data[colname])
                except (ValueError, TypeError):
                    pass
            else:
                if isinstance(data[colname], str):
                    data[colname] = parse_value_type(data[colname])
    return model_class(**data)

def parse_value_type(value: Optional[str]) -> Any:
    if value is None:
        return None

    val = value.strip()

    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False

    if val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
        return int(val)

    if val.startswith(('{', '[', '"')) and len(val) > 1:
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            pass

    return value

async def cache_get(key: str) -> Optional[Dict]:
    if not redis_client:
        return None
    try:
        data = await redis_client.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None

async def cache_set(key: str, data: Dict, ttl: int = 3600):
    if not redis_client:
        return
    try:
        await redis_client.setex(key, ttl, json.dumps(data, default=str))
    except Exception:
        pass

async def cache_delete(key: str):
    if not redis_client:
        return
    try:
        await redis_client.delete(key)
    except Exception:
        pass

async def get_or_cache(key: str, fetch_func, ttl: int = 3600):
    cached = await cache_get(key)
    if cached:
        return cached

    data = await fetch_func()
    if data:
        await cache_set(key, orm_to_dict(data) if hasattr(data, '__table__') else data, ttl)
    return data
