"""Disabled-by-default WHOOP OAuth v2 aggregate request adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlencode, urlparse

from .models import CaptureMode, ConsentState


WHOOP_AUTHORIZATION_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_V2_ROOT = "https://api.prod.whoop.com/developer/v2"
DEFAULT_SCOPES = ("offline", "read:cycles", "read:recovery")
ALLOWED_SCOPES = {
    "offline",
    "read:recovery",
    "read:cycles",
    "read:workout",
    "read:sleep",
    "read:profile",
    "read:body_measurement",
}


class IntegrationDisabled(RuntimeError):
    pass


class ConsentRequired(RuntimeError):
    pass


@dataclass(frozen=True)
class ServerOAuthConfig:
    client_id: str
    client_secret: str = field(repr=False)
    redirect_uri: str

    def __post_init__(self) -> None:
        if not self.client_id or not self.client_secret:
            raise ValueError("WHOOP server credentials are required")
        redirect = urlparse(self.redirect_uri)
        if redirect.scheme != "https" or not redirect.netloc:
            raise ValueError("WHOOP gateway redirect URI must use HTTPS")

    def tablet_config(self) -> Mapping[str, object]:
        """Return the deliberately secret-free integration state for the tablet."""
        return {"provider": "whoop", "enabled": False}


@dataclass(frozen=True, repr=False)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    form: Mapping[str, str] | None = None

    def __repr__(self) -> str:
        return f"HttpRequest(method={self.method!r}, url={self.url!r}, credentials='[REDACTED]')"

    def redacted(self) -> Mapping[str, object]:
        safe_headers = {
            name: "[REDACTED]" if name.lower() == "authorization" else value
            for name, value in self.headers.items()
        }
        safe_form = None
        if self.form is not None:
            safe_form = {
                name: "[REDACTED]"
                if name in {"client_secret", "code", "refresh_token", "access_token"}
                else value
                for name, value in self.form.items()
            }
        return {"method": self.method, "url": self.url, "headers": safe_headers, "form": safe_form}


class WhoopAggregateSource:
    """Builds consented server requests; it never provides live heart-rate samples."""

    source_id = "whoop-aggregate"
    capture_mode = CaptureMode.AGGREGATE

    def __init__(
        self,
        config: ServerOAuthConfig,
        *,
        scopes: tuple[str, ...] = DEFAULT_SCOPES,
        enabled: bool = False,
    ):
        unknown = set(scopes) - ALLOWED_SCOPES
        if unknown:
            raise ValueError(f"unsupported WHOOP scopes: {', '.join(sorted(unknown))}")
        if not scopes:
            raise ValueError("at least one WHOOP scope is required")
        self._config = config
        self.scopes = tuple(dict.fromkeys(scopes))
        self.enabled = enabled

    def authorization_url(self, *, state: str, consent: ConsentState) -> str:
        self._require_enabled()
        if consent is not ConsentState.GRANTED:
            raise ConsentRequired("WHOOP authorization requires explicit biometric consent")
        if len(state) < 8:
            raise ValueError("OAuth state must contain at least eight characters")
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._config.client_id,
                "redirect_uri": self._config.redirect_uri,
                "scope": " ".join(self.scopes),
                "state": state,
            }
        )
        return f"{WHOOP_AUTHORIZATION_URL}?{query}"

    def exchange_code_request(self, code: str) -> HttpRequest:
        self._require_enabled()
        if not code:
            raise ValueError("authorization code is required")
        return self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._config.redirect_uri,
            }
        )

    def refresh_request(self, refresh_token: str) -> HttpRequest:
        self._require_enabled()
        if not refresh_token:
            raise ValueError("refresh token is required")
        return self._token_request(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": " ".join(self.scopes),
            }
        )

    def revoke_request(self, access_token: str) -> HttpRequest:
        self._require_enabled()
        return self._bearer_request("DELETE", f"{WHOOP_API_V2_ROOT}/user/access", access_token)

    def aggregate_request(self, resource: str, access_token: str) -> HttpRequest:
        self._require_enabled()
        paths = {
            "cycles": "cycle",
            "recovery": "recovery",
            "workouts": "activity/workout",
        }
        if resource not in paths:
            raise ValueError("aggregate resource must be cycles, recovery, or workouts")
        return self._bearer_request(
            "GET", f"{WHOOP_API_V2_ROOT}/{paths[resource]}", access_token
        )

    def _token_request(self, form: Mapping[str, str]) -> HttpRequest:
        return HttpRequest(
            method="POST",
            url=WHOOP_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            form={
                **form,
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
            },
        )

    @staticmethod
    def _bearer_request(method: str, url: str, access_token: str) -> HttpRequest:
        if not access_token:
            raise ValueError("access token is required")
        return HttpRequest(
            method=method,
            url=url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise IntegrationDisabled("WHOOP aggregate context is disabled")


class WhoopProviderError(RuntimeError):
    """A response-safe provider error that deliberately drops response payloads."""

    def __init__(self, status: int):
        super().__init__(f"WHOOP request failed with status {status}")
        self.status = status
