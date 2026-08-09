"""cPanel / reverse-proxy helpers and API CORS for the Flutter app."""

from django.http import HttpResponse


class CpanelHttpsMiddleware:
    """Treat cPanel SSL as HTTPS so Secure cookies and CSRF Origin checks work.

    Passenger often receives HTTP internally with HTTPS=on instead of
    X-Forwarded-Proto, which makes Django drop CSRF/session cookies.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        forwarded = (request.META.get("HTTP_X_FORWARDED_PROTO") or "").split(",")[0].strip()
        if forwarded not in {"http", "https"}:
            if request.META.get("HTTPS") == "on" or request.META.get("HTTP_X_FORWARDED_SSL") == "on":
                request.META["HTTP_X_FORWARDED_PROTO"] = "https"
        return self.get_response(request)


class ApiCorsMiddleware:
    """Allow the Flutter web/desktop client to call /api/ from another origin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/") and request.method == "OPTIONS":
            response = HttpResponse()
            self._apply(response, request)
            return response
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            self._apply(response, request)
        return response

    def _apply(self, response, request):
        origin = request.headers.get("Origin") or "*"
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Vary"] = "Origin"
        return response
