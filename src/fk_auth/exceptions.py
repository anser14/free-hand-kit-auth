"""API exceptions with explicit public authentication semantics."""

from rest_framework import status
from rest_framework.exceptions import APIException


class PublicTokenAuthenticationFailed(APIException):
    """Return a 401 for invalid credentials submitted to a public token route."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication credentials were invalid."
    default_code = "authentication_failed"
