from functools import wraps
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_300_MULTIPLE_CHOICES, HTTP_503_SERVICE_UNAVAILABLE

# Cache decorator constants
CACHE_DECORATOR_PREFIX = 'cd_'
DEFAULT_CACHE_TIMEOUT = 300

def cache_response(timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Cache the response of the view method for a given timeout (in seconds).
    """
    def decorator(func):
        @wraps(func)
        def _wrapped_view(viewset, request, *args, **kwargs):
            cache_key = f'{CACHE_DECORATOR_PREFIX}_{viewset.__class__.__name__}_{func.__name__}_{request.path}'
            cached_res = cache.get(cache_key)

            if cached_res:
                return Response(cached_res['data'], status=cached_res['status_code'])

            # If no cache, call the original view method
            response = func(viewset, request, *args, **kwargs)

            # Cache the result before returning the response, but only if the response is successful
            if response.status_code >= HTTP_200_OK and response.status_code < HTTP_300_MULTIPLE_CHOICES:
                cached_res = { 'status_code': response.status_code, 'data': response.data }
                cache.set(cache_key, cached_res, timeout)

            return response
        return _wrapped_view
    return decorator
