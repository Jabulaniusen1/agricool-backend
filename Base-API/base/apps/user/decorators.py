from django.http import JsonResponse
# from rest_framework.exceptions import PermissionDenied

def coldtivate_authenticated_user(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # raise PermissionDenied({'error': 'Unauthorized' })
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view
