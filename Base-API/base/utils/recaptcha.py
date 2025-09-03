"""
reCAPTCHA utility functions for validating CAPTCHA challenges
"""
import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError


class RecaptchaError(ValidationError):
    """Custom exception for reCAPTCHA validation errors"""
    pass


def verify_recaptcha(recaptcha_response: str) -> bool:
    """
    Verify reCAPTCHA response with Google's reCAPTCHA API
    
    Args:
        recaptcha_response: The response token from reCAPTCHA widget
        
    Returns:
        bool: True if verification successful, False otherwise
        
    Raises:
        RecaptchaError: If reCAPTCHA is required but verification fails
    """
    # If reCAPTCHA is disabled, skip validation
    if not getattr(settings, 'RECAPTCHA_ENABLED', False):
        return True
    
    # reCAPTCHA is enabled but no response provided
    if not recaptcha_response:
        raise RecaptchaError("reCAPTCHA verification required")
    
    # Get secret key from settings
    secret_key = getattr(settings, 'RECAPTCHA_SECRET_KEY', None)
    if not secret_key:
        raise RecaptchaError("reCAPTCHA configuration error")
    
    # Verify with Google's API
    verification_url = 'https://www.google.com/recaptcha/api/siteverify'
    data = {
        'secret': secret_key,
        'response': recaptcha_response
    }
    
    try:
        response = requests.post(verification_url, data=data, timeout=10)
        result = response.json()
        
        if result.get('success', False):
            return True
        else:
            error_codes = result.get('error-codes', [])
            raise RecaptchaError(f"reCAPTCHA verification failed: {', '.join(error_codes)}")
            
    except requests.RequestException as e:
        raise RecaptchaError(f"reCAPTCHA verification service unavailable: {str(e)}")


def validate_recaptcha_field(data: dict, field_name: str = 'recaptcha_response') -> None:
    """
    Validate reCAPTCHA response from request data
    
    Args:
        data: Request data dictionary
        field_name: Name of the reCAPTCHA field (default: 'recaptcha_response')
        
    Raises:
        RecaptchaError: If reCAPTCHA validation fails
    """
    recaptcha_response = data.get(field_name)
    verify_recaptcha(recaptcha_response)


# Decorator for view methods
def require_recaptcha(field_name: str = 'recaptcha_response'):
    """
    Decorator to require reCAPTCHA validation for view methods
    
    Args:
        field_name: Name of the reCAPTCHA field in request data
    """
    def decorator(func):
        def wrapper(self, request, *args, **kwargs):
            validate_recaptcha_field(request.data, field_name)
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator