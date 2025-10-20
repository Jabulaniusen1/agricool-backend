"""
Content Security Policy (CSP) middleware for Django REST API
"""
import secrets
import base64

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
HTML_CSP_RO = (
    "default-src 'none'; "
    "script-src 'self' 'nonce-{nonce}'; "
    "style-src 'self' 'nonce-{nonce}'; "
    "img-src 'self' data: blob:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "worker-src 'self'; manifest-src 'self'; media-src 'self' blob:; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'; "
    "upgrade-insecure-requests"
)

class CSPMiddleware:
    """
    Middleware to add Content Security Policy headers to all responses.
    
    Features:
    - Nonce-based CSP for HTML responses (eliminates unsafe-inline)
    - Restrictive API CSP enforcement
    - Comprehensive security headers suite
    - Respects existing CSP headers set by views
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate nonce per request
        request.csp_nonce = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode()
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        # Skip if CSP already set by view or upstream proxy
        if "Content-Security-Policy" in response.headers or \
           "Content-Security-Policy-Report-Only" in response.headers:
            return response

        # Ensure Content-Type is always set (prevents MIME-sniffing attacks)
        if "Content-Type" not in response.headers:
            # Default to JSON for API responses without Content-Type
            response.headers["Content-Type"] = "application/json; charset=utf-8"

        ctype = response.headers.get("Content-Type", "")
        if ctype.startswith("text/html"):
            response.headers.setdefault(
                "Content-Security-Policy-Report-Only",
                HTML_CSP_RO.format(nonce=getattr(request, "csp_nonce", ""))
            )
        else:
            response.headers.setdefault("Content-Security-Policy", API_CSP)

        # Additional API hardening headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("X-Frame-Options", "DENY")

        return response