from django.core import checks
from django.test import override_settings

from fk_auth.conf import configuration_issues, get_settings, get_verification_method


def test_defaults_are_merged_without_mutating_host_settings() -> None:
    with override_settings(
        FREEHAND_KIT_AUTH={"LOGIN": {"IDENTIFIERS": ("email",)}, "JWT": {"SIGNING_KEY": "x"}}
    ):
        config = get_settings()

    assert config["LOGIN"]["IDENTIFIERS"] == ("email",)
    assert config["JWT"]["ROTATE_REFRESH_TOKENS"] is True


def test_missing_jwt_signing_key_is_a_system_check_error() -> None:
    with override_settings(FREEHAND_KIT_AUTH={"JWT": {"SIGNING_KEY": ""}}):
        issues = configuration_issues()

    assert any(issue.id == "fk_auth.E006" for issue in issues)


def test_django_registers_the_package_checks() -> None:
    with override_settings(
        FREEHAND_KIT_AUTH={
            "JWT": {"SIGNING_KEY": "test-only-signing-key-at-least-32-bytes"},
            "THROTTLE": {"REQUIRE_SHARED_CACHE": False},
        }
    ):
        issues = checks.run_checks(tags=["fk_auth"])

    assert not [issue for issue in issues if issue.level >= checks.ERROR]


def test_email_cannot_be_a_generic_profile_write_field() -> None:
    with override_settings(
        FREEHAND_KIT_AUTH={
            "JWT": {"SIGNING_KEY": "x"},
            "USER": {
                "PROFILE_READ_FIELDS": ("email",),
                "PROFILE_WRITE_FIELDS": ("email",),
            },
        }
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_auth.E018" for issue in issues)


def test_legacy_verification_mode_uses_link_only_when_a_template_exists() -> None:
    with override_settings(
        FREEHAND_KIT_AUTH={
            "JWT": {"SIGNING_KEY": "x"},
            "EMAIL": {"VERIFICATION_URL_TEMPLATE": "https://app.example.test/verify?token={token}"},
        }
    ):
        assert get_verification_method() == "link"

    with override_settings(FREEHAND_KIT_AUTH={"JWT": {"SIGNING_KEY": "x"}}):
        assert get_verification_method() == "token"


def test_otp_configuration_requires_redis_and_a_dedicated_pepper() -> None:
    with override_settings(
        FREEHAND_KIT_AUTH={
            "JWT": {"SIGNING_KEY": "x"},
            "VERIFICATION": {"METHOD": "otp", "OTP": {"REDIS_URL": ""}},
        }
    ):
        issues = configuration_issues()

    issue_ids = {issue.id for issue in issues}
    assert "fk_auth.E024" in issue_ids
    assert "fk_auth.E026" in issue_ids


def test_short_hmac_signing_key_is_a_system_check_error() -> None:
    with override_settings(FREEHAND_KIT_AUTH={"JWT": {"SIGNING_KEY": "too-short"}}):
        issues = configuration_issues()

    assert any(issue.id == "fk_auth.E035" for issue in issues)


def test_shared_cache_is_required_by_the_production_default() -> None:
    with override_settings(
        FREEHAND_KIT_AUTH={"JWT": {"SIGNING_KEY": "test-only-signing-key-at-least-32-bytes"}}
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_auth.E049" for issue in issues)


def test_roles_require_a_valid_server_owned_default() -> None:
    with override_settings(
        FREEHAND_KIT_AUTH={
            "JWT": {"SIGNING_KEY": "test-only-signing-key-at-least-32-bytes"},
            "THROTTLE": {"REQUIRE_SHARED_CACHE": False},
            "ROLES": {"ENABLED": True, "DEFAULT_SIGNUP_ROLE": "missing", "DEFINITIONS": {}},
        }
    ):
        issues = configuration_issues()

    assert any(issue.id == "fk_auth.E053" for issue in issues)
