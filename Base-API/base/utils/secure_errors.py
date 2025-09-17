"""
Secure error handling utilities to prevent information disclosure vulnerabilities.
"""
import logging
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def log_and_return_safe_error(exception, error_message, status_code, context=None):
    """
    Log the actual exception details securely and return a safe error response.
    
    Args:
        exception: The caught exception
        error_message: Safe error message to return to client
        status_code: HTTP status code
        context: Additional context for logging
    
    Returns:
        Response object with safe error message
    """
    # Log the actual exception for debugging (server-side only)
    if context:
        logger.error(f"Error in {context}: {type(exception).__name__}: {str(exception)}")
    else:
        logger.error(f"{type(exception).__name__}: {str(exception)}")
    
    # Return safe error message to client
    return Response(
        {"error": error_message}, 
        status=status_code
    )


def handle_authentication_error(exception, context=None):
    """Handle authentication errors safely."""
    return log_and_return_safe_error(
        exception,
        "Authentication failed",
        status.HTTP_401_UNAUTHORIZED,
        context
    )


def handle_authorization_error(exception, context=None):
    """Handle authorization errors safely."""
    return log_and_return_safe_error(
        exception,
        "Access denied",
        status.HTTP_403_FORBIDDEN,
        context
    )


def handle_external_service_error(exception, context=None):
    """Handle external service errors safely."""
    return log_and_return_safe_error(
        exception,
        "External service unavailable",
        status.HTTP_503_SERVICE_UNAVAILABLE,
        context
    )


def handle_validation_error(exception, context=None):
    """Handle validation errors safely."""
    return log_and_return_safe_error(
        exception,
        "Invalid input provided",
        status.HTTP_400_BAD_REQUEST,
        context
    )


def handle_internal_error(exception, context=None):
    """Handle internal errors safely."""
    return log_and_return_safe_error(
        exception,
        "An internal error occurred",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        context
    )