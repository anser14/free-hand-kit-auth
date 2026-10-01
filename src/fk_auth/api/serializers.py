"""DRF serializers whose user-model fields are resolved from host configuration."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model, password_validation
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import serializers

from fk_auth.conf import (
    get_otp_settings,
    get_registration_fields,
    get_settings,
    get_user_field_names,
    get_user_model_email_field,
    get_verification_method,
)
from fk_auth.services.otp import OTP_ALPHABETS


class LoginSerializer(serializers.Serializer[Any]):
    identifier = serializers.CharField(trim_whitespace=True, max_length=254)
    password = serializers.CharField(
        trim_whitespace=False, write_only=True, style={"input_type": "password"}
    )


class EmailVerificationTokenSerializer(serializers.Serializer[Any]):
    """Request body for link and token email verification."""

    token = serializers.CharField(trim_whitespace=True, max_length=4096)


class JWTVerificationTokenSerializer(serializers.Serializer[Any]):
    """Request body for validating an issued access JWT."""

    token = serializers.CharField(trim_whitespace=True, max_length=4096)


class EmailSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()


class EmailOTPVerificationSerializer(serializers.Serializer[Any]):
    """Verification request schema exposed only when OTP mode is selected."""

    email = serializers.EmailField()
    otp = serializers.CharField(trim_whitespace=True, write_only=True)

    def validate_otp(self, value: str) -> str:
        settings = get_otp_settings()
        normalized = value.upper()
        alphabet = OTP_ALPHABETS[str(settings["ALPHABET"])]
        if len(normalized) != int(settings["LENGTH"]) or any(
            character not in alphabet for character in normalized
        ):
            raise serializers.ValidationError("Invalid verification OTP.")
        return normalized


def verification_serializer_class() -> type[serializers.Serializer[Any]]:
    """Return the mode-specific request schema for the email verify endpoint."""

    if get_verification_method() == "otp":
        return EmailOTPVerificationSerializer
    return EmailVerificationTokenSerializer


class RefreshSerializer(serializers.Serializer[Any]):
    refresh = serializers.CharField(trim_whitespace=True)


class PasswordChangeSerializer(serializers.Serializer[Any]):
    old_password = serializers.CharField(trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate_old_password(self, value: str) -> str:
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        password_validation.validate_password(value, self.context["request"].user)
        return value


class PasswordResetConfirmSerializer(serializers.Serializer[Any]):
    uid = serializers.CharField(trim_whitespace=True)
    token = serializers.CharField(trim_whitespace=True)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)


def signup_serializer_class() -> type[serializers.ModelSerializer[Any]]:
    """Build a model serializer for the active AUTH_USER_MODEL at runtime."""

    user_model = get_user_model()
    registration_fields = get_registration_fields()
    email_field = get_user_model_email_field()

    class SignupSerializer(serializers.ModelSerializer[Any]):
        password = serializers.CharField(
            trim_whitespace=False, write_only=True, style={"input_type": "password"}
        )
        password_confirm = serializers.CharField(
            trim_whitespace=False,
            write_only=True,
            style={"input_type": "password"},
        )

        class Meta:
            model = user_model
            fields = (*registration_fields, "password", "password_confirm")
            extra_kwargs = (
                {email_field: {"required": True}}
                if email_field and email_field in registration_fields
                else {}
            )

        def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
            password = attrs.get("password")
            if password != attrs.pop("password_confirm", None):
                raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
            if email_field and email_field in attrs:
                # Login and recovery lookups are case-insensitive.  Store one canonical
                # representation so the database uniqueness constraint enforces that rule.
                attrs[email_field] = str(attrs[email_field]).strip().casefold()

            lookup_fields: list[str] = []
            identifiers = get_settings()["LOGIN"]["IDENTIFIERS"]
            if "email" in identifiers and email_field:
                lookup_fields.append(email_field)
            if "username" in identifiers and user_model.USERNAME_FIELD not in lookup_fields:
                lookup_fields.append(user_model.USERNAME_FIELD)
            identity_values = [
                str(attrs[field]).strip() for field in lookup_fields if field in attrs
            ]
            if identity_values:
                query = Q()
                for value in identity_values:
                    for field_name in lookup_fields:
                        query |= Q(**{f"{field_name}__iexact": value})
                if user_model._default_manager.filter(query).exists():
                    raise serializers.ValidationError(
                        "An account with one of these login identifiers already exists."
                    )
            password_validation.validate_password(password)
            return attrs

        def create(self, validated_data: dict[str, Any]) -> Any:
            password = validated_data.pop("password")
            # The pre-flight lookup gives a helpful error in normal use, but the
            # database is the only authority during concurrent registrations.
            try:
                with transaction.atomic():
                    return user_model._default_manager.create_user(
                        password=password, **validated_data
                    )
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    "An account with one of these login identifiers already exists."
                ) from exc

    return SignupSerializer


def profile_serializer_class() -> type[serializers.ModelSerializer[Any]]:
    """Build the safe, host-controlled `me` representation for the active user model."""

    user_model = get_user_model()
    read_fields = get_user_field_names("PROFILE_READ_FIELDS")
    write_fields = get_user_field_names("PROFILE_WRITE_FIELDS")

    class ProfileSerializer(serializers.ModelSerializer[Any]):
        class Meta:
            model = user_model
            fields = ("id", *read_fields)
            read_only_fields = (
                "id",
                *(field for field in read_fields if field not in write_fields),
            )

    return ProfileSerializer
