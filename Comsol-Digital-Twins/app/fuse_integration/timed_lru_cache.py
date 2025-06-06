from functools import wraps
import time

# Cache TTL in milliseconds
CACHE_TTL_MS = 750

def timed_lru_cache(ttl_ms=CACHE_TTL_MS, maxsize=128):
    """
    Decorator that creates a cache with a time-to-live (TTL).
    Args:
        ttl_ms: Time to live in milliseconds
        maxsize: Maximum size of the cache
    """
    def decorator(func):
        # Create a cache to store timestamps along with results
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key_args = args[1:] if args and hasattr(args[0], '__class__') else args
            key = str(key_args) + str(kwargs)
            now = time.time() * 1000  # Current time in milliseconds

            if key in cache:
                result, timestamp = cache[key]
                # Check if the cached result is still valid
                if now - timestamp < ttl_ms:
                    return result
                else:
                    del cache[key]

            # Calculate new result and store with timestamp
            result = func(*args, **kwargs)
            cache[key] = (result, now)

            # Implement LRU by removing oldest entries if cache is too large
            if len(cache) > maxsize:
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                del cache[oldest_key]

            return result
        return wrapper
    return decorator
