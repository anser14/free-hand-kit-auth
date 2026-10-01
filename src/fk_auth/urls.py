"""Stable mount point for Freehand Kit Auth API and OpenAPI routes."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from fk_auth.api.views import (
    EmailResendView,
    EmailVerifyView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SignupView,
    TokenRefreshView,
    TokenVerifyView,
)
from fk_auth.conf import verification_is_required

app_name = "fk_auth"
urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/forgot/", PasswordResetRequestView.as_view(), name="password-forgot"),
    path("password/reset/", PasswordResetConfirmView.as_view(), name="password-reset"),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("me/", MeView.as_view(), name="me"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="fk_auth:schema"), name="swagger-ui"),
]

if verification_is_required():
    urlpatterns[1:1] = [
        path("email/verify/", EmailVerifyView.as_view(), name="email-verify"),
        path("email/resend/", EmailResendView.as_view(), name="email-resend"),
    ]
