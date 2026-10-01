"""Documented DRF account and token endpoints for Freehand Kit Auth."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from fk_auth.api.serializers import (
    EmailSerializer,
    JWTVerificationTokenSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    RefreshSerializer,
    profile_serializer_class,
    signup_serializer_class,
    verification_serializer_class,
)
from fk_auth.conf import (
    get_settings,
    get_user_model_email_field,
    get_verification_method,
    verification_is_required,
)
from fk_auth.exceptions import PublicTokenAuthenticationFailed
from fk_auth.services.credentials import (
    InvalidOneTimeCredential,
    consume_credential,
    has_verified_email,
    issue_credential,
    mark_email_verified,
)
from fk_auth.services.emails import send_email_verification, send_password_reset
from fk_auth.services.otp import (
    InvalidOTP,
    OTPResendSuppressed,
    OTPStoreUnavailable,
    consume_otp,
    issue_otp,
)
from fk_auth.services.users import (
    InvalidCredentials,
    UnverifiedEmail,
    authenticate_identifier,
    get_user_email,
)
from fk_auth.throttles import (
    EmailThrottle,
    LoginThrottle,
    PasswordResetThrottle,
    SignupThrottle,
    TokenThrottle,
)
from fk_auth.tokens import (
    FreehandAccessToken,
    FreehandJWTAuthentication,
    blacklist_refresh_token,
    issue_token_pair,
    refresh_token_pair,
    revoke_user_refresh_tokens,
)


class PublicAuthAPIView(APIView):
    """Base for public routes with an explicit spectacular schema implementation."""

    authentication_classes: list[type] = []
    permission_classes = [permissions.AllowAny]
    schema = AutoSchema()


class ProtectedAuthAPIView(APIView):
    """Base for routes secured by the Freehand-configured JWT backend."""

    authentication_classes = [FreehandJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    schema = AutoSchema()


class VerificationStoreUnavailable(APIException):
    """Return a retryable error without exposing Redis implementation details."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Email verification is temporarily unavailable. Please try again later."
    default_code = "verification_unavailable"


def _verification_lifetime() -> int:
    return int(get_settings()["EMAIL"]["VERIFICATION_TOKEN_LIFETIME_SECONDS"])


PROFILE_SCHEMA_SERIALIZER = profile_serializer_class()


def _send_verification_for_user(user: object, *, is_resend: bool) -> bool:
    email = get_user_email(user)
    if not email:
        return False
    method = get_verification_method()
    try:
        if method == "otp":
            credential = issue_otp(user=user, email=email, is_resend=is_resend)
        else:
            credential = issue_credential(
                user=user,
                purpose="email_verification",
                email=email,
                lifetime_seconds=_verification_lifetime(),
            )
    except OTPResendSuppressed:
        return False
    except OTPStoreUnavailable as exc:
        raise VerificationStoreUnavailable from exc
    send_email_verification(user=user, email=email, credential=credential, method=method)
    return True


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=signup_serializer_class(),
    responses={
        201: OpenApiResponse(description="Account created."),
        400: OpenApiResponse(description="Invalid input."),
    },
)
class SignupView(PublicAuthAPIView):
    """Create a host-model user from only explicitly configured safe fields."""

    throttle_classes = [SignupThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        if not get_settings()["REGISTRATION"]["ENABLED"]:
            raise NotFound()

        serializer = signup_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if verification_is_required():
            _send_verification_for_user(user, is_resend=False)
        return Response({"detail": "Account created."}, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Freehand Kit Auth"],
    responses={
        200: OpenApiResponse(description="Email verified."),
        400: OpenApiResponse(description="Invalid or expired verification credential."),
    },
)
class EmailVerifyView(PublicAuthAPIView):
    """Consume the selected one-time email-verification credential."""

    throttle_classes = [EmailThrottle]

    def get_serializer(self, *args: Any, **kwargs: Any) -> Serializer[Any]:
        """Expose the selected token or OTP request shape to drf-spectacular."""

        return verification_serializer_class()(*args, **kwargs)

    def post(self, request):  # type: ignore[no-untyped-def]
        if not verification_is_required():
            raise NotFound()

        method = get_verification_method()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if method == "otp":
            otp_serializer = serializer
            try:
                user_id = consume_otp(
                    email=otp_serializer.validated_data["email"],
                    otp=otp_serializer.validated_data["otp"],
                )
            except InvalidOTP as exc:
                raise ValidationError(
                    {"otp": "Invalid, expired, or exhausted verification OTP."}
                ) from exc
            except OTPStoreUnavailable as exc:
                raise VerificationStoreUnavailable from exc

            from django.contrib.auth import get_user_model

            try:
                user = get_user_model()._default_manager.get(pk=user_id)
            except get_user_model().DoesNotExist as exc:
                raise ValidationError({"otp": "Invalid or expired verification OTP."}) from exc
            email = str(otp_serializer.validated_data["email"])
            current_email = get_user_email(user)
            if not current_email or current_email.casefold() != email.casefold():
                raise ValidationError({"otp": "Invalid or expired verification OTP."})
            mark_email_verified(user=user, email=email)
            return Response({"detail": "Email verified."})

        try:
            consume_credential(
                token=serializer.validated_data["token"],
                purpose="email_verification",
            )
        except InvalidOneTimeCredential as exc:
            raise ValidationError({"token": "Invalid or expired verification token."}) from exc
        return Response({"detail": "Email verified."})


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=EmailSerializer,
    responses={202: OpenApiResponse(description="A verification email will be sent if eligible.")},
)
class EmailResendView(PublicAuthAPIView):
    """Resend a verification credential without revealing account existence."""

    throttle_classes = [EmailThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_field = get_user_model_email_field()
        if email_field:
            from django.contrib.auth import get_user_model

            candidates = list(
                get_user_model()._default_manager.filter(
                    **{f"{email_field}__iexact": serializer.validated_data["email"]}
                )[:2]
            )
            if len(candidates) == 1 and not has_verified_email(
                user=candidates[0], email=serializer.validated_data["email"]
            ):
                _send_verification_for_user(candidates[0], is_resend=True)
        return Response(
            {"detail": "If the account is eligible, a verification email will be sent."},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(description="Access and refresh tokens."),
        400: OpenApiResponse(description="Invalid credentials."),
    },
)
class LoginView(PublicAuthAPIView):
    """Authenticate an email or username identity and issue a JWT token pair."""

    throttle_classes = [LoginThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = authenticate_identifier(
                identifier=serializer.validated_data["identifier"],
                password=serializer.validated_data["password"],
            )
        except InvalidCredentials as exc:
            raise PublicTokenAuthenticationFailed(
                "No active account found with the given credentials."
            ) from exc
        except UnverifiedEmail as exc:
            raise PublicTokenAuthenticationFailed(
                "Email verification is required before login.", code="email_unverified"
            ) from exc
        return Response(issue_token_pair(user))


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=RefreshSerializer,
    responses={
        200: OpenApiResponse(description="A fresh access token and, when enabled, refresh token.")
    },
)
class TokenRefreshView(PublicAuthAPIView):
    throttle_classes = [TokenThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(refresh_token_pair(serializer.validated_data["refresh"]))
        except Exception as exc:
            raise PublicTokenAuthenticationFailed(
                "Refresh token is invalid or expired.", code="token_not_valid"
            ) from exc


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=JWTVerificationTokenSerializer,
    responses={200: OpenApiResponse(description="Token is valid.")},
)
class TokenVerifyView(PublicAuthAPIView):
    throttle_classes = [TokenThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = JWTVerificationTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            FreehandAccessToken(serializer.validated_data["token"])
        except Exception as exc:
            raise PublicTokenAuthenticationFailed(
                "Token is invalid or expired.", code="token_not_valid"
            ) from exc
        return Response({"detail": "Token is valid."})


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=RefreshSerializer,
    responses={205: OpenApiResponse(description="Refresh token revoked.")},
)
class LogoutView(PublicAuthAPIView):
    throttle_classes = [TokenThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            blacklist_refresh_token(serializer.validated_data["refresh"])
        except Exception as exc:
            raise ValidationError(
                {"refresh": "Refresh token is invalid or already revoked."}
            ) from exc
        return Response(status=status.HTTP_205_RESET_CONTENT)


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=EmailSerializer,
    responses={
        202: OpenApiResponse(description="A reset email will be sent if the account exists.")
    },
)
class PasswordResetRequestView(PublicAuthAPIView):
    """Send Django's single-use password-reset token without account enumeration."""

    throttle_classes = [PasswordResetThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_field = get_user_model_email_field()
        if email_field:
            from django.contrib.auth import get_user_model

            users = list(
                get_user_model()._default_manager.filter(
                    **{f"{email_field}__iexact": serializer.validated_data["email"]}
                )[:2]
            )
            if len(users) == 1 and getattr(users[0], "is_active", True):
                user = users[0]
                send_password_reset(
                    user=user,
                    email=serializer.validated_data["email"],
                    uid=urlsafe_base64_encode(force_bytes(user.pk)),
                    token=default_token_generator.make_token(user),
                )
        return Response(
            {"detail": "If the account exists, a password-reset email will be sent."},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=PasswordResetConfirmSerializer,
    responses={204: OpenApiResponse(description="Password reset complete.")},
)
class PasswordResetConfirmView(PublicAuthAPIView):
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            from django.contrib.auth import get_user_model

            user_id = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = get_user_model()._default_manager.get(pk=user_id)
        except Exception as exc:
            raise ValidationError({"token": "Invalid password-reset token."}) from exc
        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            raise ValidationError({"token": "Invalid password-reset token."})
        from django.contrib.auth import password_validation

        password_validation.validate_password(serializer.validated_data["new_password"], user)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        revoke_user_refresh_tokens(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Freehand Kit Auth"],
    request=PasswordChangeSerializer,
    responses={204: OpenApiResponse(description="Password changed.")},
)
class PasswordChangeView(ProtectedAuthAPIView):
    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        revoke_user_refresh_tokens(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Freehand Kit Auth"],
    responses={200: PROFILE_SCHEMA_SERIALIZER},
)
class MeView(ProtectedAuthAPIView):
    """Read and update only the host-approved profile fields."""

    def get(self, request):  # type: ignore[no-untyped-def]
        return Response(profile_serializer_class()(request.user).data)

    @extend_schema(request=PROFILE_SCHEMA_SERIALIZER, responses={200: PROFILE_SCHEMA_SERIALIZER})
    def patch(self, request):  # type: ignore[no-untyped-def]
        serializer = profile_serializer_class()(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
