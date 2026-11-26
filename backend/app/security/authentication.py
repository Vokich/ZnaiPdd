from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import SAFE_METHODS


def browser_exception_handler(exc, context):
    from rest_framework.views import exception_handler

    response = exception_handler(exc, context)
    if response is not None and isinstance(exc, NotAuthenticated):
        response.data['code'] = exc.get_codes()
    return response


class BrowserSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        # Login and registration also need CSRF protection for anonymous visitors.
        authentication = super().authenticate(request)
        if authentication is None and request.method not in SAFE_METHODS:
            self.enforce_csrf(request)
        return authentication
