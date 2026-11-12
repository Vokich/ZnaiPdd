from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import SAFE_METHODS


class BrowserSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        # Login and registration also need CSRF protection for anonymous visitors.
        authentication = super().authenticate(request)
        if authentication is None and request.method not in SAFE_METHODS:
            self.enforce_csrf(request)
        return authentication
