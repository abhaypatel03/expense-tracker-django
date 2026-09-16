import time
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date


class SeparateAdminSessionMiddleware(SessionMiddleware):
    """Use a separate session cookie for admin and website requests."""

    def __init__(self, get_response):
        super().__init__(get_response)
        engine = import_module(settings.SESSION_ENGINE)
        self.SessionStore = engine.SessionStore

    def _cookie_name(self, request):
        if request.path.startswith(("/admin/", "/admin-dashboard/")):
            return "admin_sessionid"
        return "website_sessionid"

    def process_request(self, request):
        cookie_name = self._cookie_name(request)
        session_key = request.COOKIES.get(cookie_name)

        if session_key is None:
            session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)

        request.session = self.SessionStore(session_key)

    def process_response(self, request, response):
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        cookie_name = self._cookie_name(request)

        if cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            patch_vary_headers(response, ("Cookie",))
        else:
            if accessed:
                patch_vary_headers(response, ("Cookie",))

            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if response.status_code >= 500:
                    return response

                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires = http_date(time.time() + max_age)

                request.session.save()

                response.set_cookie(
                    cookie_name,
                    request.session.session_key,
                    max_age=max_age,
                    expires=expires,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    path=settings.SESSION_COOKIE_PATH,
                    secure=settings.SESSION_COOKIE_SECURE or None,
                    httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                )

        return response