"""cPanel / reverse-proxy helpers."""


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
