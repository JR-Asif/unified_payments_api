import redis
import json
from typing import Optional, Tuple, Dict, Any
from app.utils.loggers import logger
from app.config import settings


redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
TTL_SECONDS = 300


class IdempotencyManager:

    @staticmethod
    def acquire_lock_or_get_status(key: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Try to claim an idempotency lock for this key. If it already exists,
        return what's cached (used for safe retries of Create Payment / Refund).

        Returns (is_new_lock, status, cached_payload).
        """
        initial_payload = {"status": "IN_PROGRESS", "data": None}

        is_inserted = redis_client.set(
            name=key,
            value=json.dumps(initial_payload),
            nx=True,
            ex=TTL_SECONDS,
        )

        if is_inserted:
            return True, None, None

        raw_data = redis_client.get(key)
        if not raw_data:
            logger.warning(f"idempotency.lock_state_missing key={key}")
            return False, None, None

        try:
            parsed_data = json.loads(raw_data)
        except json.JSONDecodeError:
            logger.warning(f"idempotency.malformed_cache key={key} raw={raw_data!r}")
            return False, None, None
        return False, parsed_data.get("status"), parsed_data.get("data")

    @staticmethod
    def commit_success(key: str, data: Dict[str, Any]):
        """Cache the successful response under the idempotency key so retries can replay it."""
        success_payload = {"status": "SUCCESS", "data": data}
        redis_client.set(name=key, value=json.dumps(success_payload), ex=TTL_SECONDS)

    @staticmethod
    def release_lock(key: str):
        """Release the lock when the upstream provider fails so retries aren't blocked by 409."""
        redis_client.delete(key)
