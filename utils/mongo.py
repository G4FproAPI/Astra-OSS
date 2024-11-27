from typing import Dict, Optional, Iterator
import redis
import json
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

USER_PREFIX = "user:"
BANNED_SET = "banned_users"
API_KEY_PREFIX = "api_key:"

def _get_user_key(user_id: str) -> str:
    return f"{USER_PREFIX}{user_id}"

def get_max_usage_for_plan(plan: str) -> int:
    usage_limits = {
        "free": 400,
        "basic": 400,
        "pro": 2000,
        "enterprise": 5000
    }
    return usage_limits.get(plan, 100)  

async def get_user(user_id: str) -> Optional[Dict]:
    try:
        user_data = redis_client.get(_get_user_key(user_id))
        return json.loads(user_data) if user_data else None
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

async def get_user_by_api_key(api_key: str) -> Optional[dict]:
    try:
        user_id = redis_client.get(f"{API_KEY_PREFIX}{api_key}")
        if user_id is None:
            return None
        return await get_user(user_id)
    except Exception as e:
        logger.error(f"Error in get_user_by_api_key: {e}")
        return None

async def add_user(user_id: str, api_key: str, plan: str = "free", burner_limit: float = None) -> None:
    try:
        if burner_limit is None:
            max_usage = get_max_usage_for_plan(plan)
        else:
            max_usage = burner_limit
            
        user_data = {
            "user_id": user_id,
            "api_key": api_key,
            "plan": plan,
            "banned": False,
            "usage": 0,
            "max_usage_per_day": max_usage,
            "total_usage_all_time": 0,
            "last_reset": int(time.time()),
            "created_at": int(time.time())
        }
        redis_client.set(_get_user_key(user_id), json.dumps(user_data))
        redis_client.set(f"{API_KEY_PREFIX}{api_key}", user_id)
    except Exception as e:
        raise

async def update_user(user_id: str, updates: Dict) -> None:
    try:
        user_data = await get_user(user_id)
        if user_data:
            if 'api_key' in updates and updates['api_key'] != user_data['api_key']:
                redis_client.delete(f"{API_KEY_PREFIX}{user_data['api_key']}")
                redis_client.set(f"{API_KEY_PREFIX}{updates['api_key']}", user_id)
            
            if 'plan' in updates:
                updates['max_usage_per_day'] = get_max_usage_for_plan(updates['plan'])
            
            user_data.update(updates)
            redis_client.set(_get_user_key(user_id), json.dumps(user_data))
            return user_data
    except Exception as e:
        raise

async def delete_user(user_id: str) -> None:
    try:
        user_data = await get_user(user_id)
        if user_data:
            redis_client.delete(_get_user_key(user_id))
            redis_client.delete(f"{API_KEY_PREFIX}{user_data['api_key']}")
            redis_client.srem(BANNED_SET, user_id)
    except Exception as e:
        raise

async def ban_user(user_id: str) -> None:
    try:
        await update_user(user_id, {"banned": True})
        redis_client.sadd(BANNED_SET, user_id)
    except Exception as e:
        raise

async def unban_user(user_id: str) -> None:
    try:
        await update_user(user_id, {"banned": False})
        redis_client.srem(BANNED_SET, user_id)
    except Exception as e:
        raise

async def get_all_banned_users() -> list:
    return list(redis_client.smembers(BANNED_SET))

async def add_usage(user_id: str, usage: float) -> None:
    try:
        user_data = await get_user(user_id)
        if not user_data:
            raise ValueError(f"No user found with ID {user_id}")

        current_time = int(time.time())
        last_reset = user_data.get('last_reset', 0)
        if (current_time - last_reset) >= 86400:  
            user_data['usage'] = 0
            user_data['last_reset'] = current_time

        new_usage = float(user_data['usage']) + usage
        new_total = float(user_data['total_usage_all_time']) + usage

        updates = {
            "usage": new_usage,
            "total_usage_all_time": new_total,
            "last_reset": user_data['last_reset']
        }
        
        await update_user(user_id, updates)
    except Exception as e:
        raise

async def get_usage(user_id: str) -> Optional[float]:
    user_data = await get_user(user_id)
    return float(user_data['usage']) if user_data else None

async def get_plan(user_id: str) -> Optional[str]:
    user_data = await get_user(user_id)
    return user_data['plan'] if user_data else None

async def get_api_key(user_id: str) -> Optional[str]:
    user_data = await get_user(user_id)
    return user_data['api_key'] if user_data else None

async def get_all_users() -> list:
    users = []
    for key in redis_client.scan_iter(f"{USER_PREFIX}*"):
        user_data = redis_client.get(key)
        if user_data:
            users.append(json.loads(user_data))
    return users

async def check_rate_limit(user_id: str) -> tuple[bool, Optional[Dict]]:
    user_data = await get_user(user_id)
    if not user_data:
        return False, None
    
    if user_data['banned']:
        return False, user_data
        
    current_usage = float(user_data['usage'])
    max_usage = float(user_data['max_usage_per_day'])
    
    return current_usage < max_usage, user_data

async def reset_user_usage(user_id: str) -> None:
    try:
        updates = {
            "usage": 0,
            "last_reset": int(time.time())
        }
        await update_user(user_id, updates)
    except Exception as e:
        raise
