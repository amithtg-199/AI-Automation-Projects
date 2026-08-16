import time
import random
import logging
from redis import Redis
from functools import wraps
from typing import Callable, Any

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Initialize a separate strict redis client for token bucket logic if REDIS_URL is provided
redis_client = None
if settings.REDIS_URL:
    try:
        redis_client = Redis.from_url(settings.REDIS_URL + "/1", decode_responses=True)
    except Exception as e:
        logger.warning(f"Could not connect to Redis for rate limiting: {e}")

def exponential_backoff_with_jitter(max_retries: int = 3, base_delay: float = 1.0) -> Callable:
    """
    Decorator for applying exponential backoff with jitter on operations that might fail with HTTP 429.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Max retries ({max_retries}) reached. Failing.")
                        raise e
                    
                    # Exponential backoff: base_delay * 2^(retry-1)
                    delay = base_delay * (2 ** (retries - 1))
                    # Add jitter: random float between 0 and base_delay
                    jitter = random.uniform(0, base_delay)
                    total_sleep = delay + jitter
                    
                    logger.warning(f"Operation failed with error: {e}. Retrying in {total_sleep:.2f} seconds (Attempt {retries}/{max_retries})")
                    time.sleep(total_sleep)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def consume_tokens(tokens_required: int = 1000) -> bool:
    """
    Centralized Token Bucket using Redis.
    Limits to 9000 tokens per minute to avoid 10,000 token limit.
    """
    if not redis_client:
        return True # Fail open if no redis
        
    bucket_key = "stlc:token_bucket:llm_calls"
    max_tokens = 9000
    refill_rate_per_sec = max_tokens / 60.0
    
    # Simple atomic token bucket script in Redis
    lua_script = """
    local bucket_key = KEYS[1]
    local tokens_required = tonumber(ARGV[1])
    local max_tokens = tonumber(ARGV[2])
    local refill_rate = tonumber(ARGV[3])
    local now = tonumber(ARGV[4])
    
    local bucket = redis.call("HMGET", bucket_key, "tokens", "last_refill")
    local current_tokens = tonumber(bucket[1]) or max_tokens
    local last_refill = tonumber(bucket[2]) or now
    
    local time_passed = math.max(0, now - last_refill)
    local new_tokens = math.min(max_tokens, current_tokens + (time_passed * refill_rate))
    
    if new_tokens >= tokens_required then
        new_tokens = new_tokens - tokens_required
        redis.call("HMSET", bucket_key, "tokens", new_tokens, "last_refill", now)
        redis.call("EXPIRE", bucket_key, 120) -- Keep alive for 2 mins
        return 1
    else:
        -- Not enough tokens, just update refill time
        redis.call("HMSET", bucket_key, "tokens", new_tokens, "last_refill", now)
        return 0
    """
    
    now = time.time()
    try:
        allowed = redis_client.eval(lua_script, 1, bucket_key, tokens_required, max_tokens, refill_rate_per_sec, now)
        return bool(allowed)
    except Exception as e:
        logger.warning(f"Token bucket evaluation failed: {e}. Defaulting to True.")
        return True

def wait_for_tokens(tokens_required: int = 1000, timeout: int = 30) -> bool:
    """
    Block until tokens are available or timeout is reached.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if consume_tokens(tokens_required):
            return True
        # Sleep for a bit before checking again
        time.sleep(0.5)
    
    logger.error(f"Timeout waiting for {tokens_required} tokens.")
    return False
