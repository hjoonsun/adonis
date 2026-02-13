from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol


@dataclass(frozen=True)
class KISAuthConfig:
    app_key: str
    app_secret: str
    base_url: str
    is_paper: bool = True

    @classmethod
    def from_env(cls) -> "KISAuthConfig":
        app_key = os.getenv("KIS_APP_KEY", "").strip()
        app_secret = os.getenv("KIS_APP_SECRET", "").strip()
        base_url = os.getenv(
            "KIS_BASE_URL", "https://openapi.koreainvestment.com:9443"
        ).strip()
        is_paper = os.getenv("KIS_IS_PAPER", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
        }

        missing = []
        if not app_key:
            missing.append("KIS_APP_KEY")
        if not app_secret:
            missing.append("KIS_APP_SECRET")
        if missing:
            raise ValueError(f"필수 환경변수가 없습니다: {', '.join(missing)}")

        return cls(
            app_key=app_key,
            app_secret=app_secret,
            base_url=base_url,
            is_paper=is_paper,
        )


@dataclass(frozen=True)
class KISToken:
    access_token: str
    expires_at: datetime
    token_type: str = "Bearer"

    def is_expired(self, now: datetime, skew_seconds: int = 30) -> bool:
        return now >= self.expires_at - timedelta(seconds=skew_seconds)


class TokenStore(Protocol):
    def load(self) -> KISToken | None:
        ...

    def save(self, token: KISToken) -> None:
        ...


class InMemoryTokenStore:
    def __init__(self) -> None:
        self._token: KISToken | None = None

    def load(self) -> KISToken | None:
        return self._token

    def save(self, token: KISToken) -> None:
        self._token = token


FetchTokenFn = Callable[[KISAuthConfig], dict]


class KISAuthClient:
    def __init__(
        self,
        config: KISAuthConfig,
        fetch_token: FetchTokenFn,
        token_store: TokenStore | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.fetch_token = fetch_token
        self.token_store = token_store or InMemoryTokenStore()
        self.clock = clock or (lambda: datetime.now(tz=timezone.utc))

    def get_access_token(self, force_refresh: bool = False) -> str:
        now = self.clock()
        cached = self.token_store.load()

        if not force_refresh and cached and not cached.is_expired(now):
            return cached.access_token

        raw = self.fetch_token(self.config)
        token = self._parse_token(raw)
        self.token_store.save(token)
        return token.access_token

    def _parse_token(self, raw: dict) -> KISToken:
        access_token = str(raw.get("access_token", "")).strip()
        if not access_token:
            raise ValueError("토큰 응답에 access_token이 없습니다")

        expires_in = raw.get("expires_in")
        if expires_in is None:
            raise ValueError("토큰 응답에 expires_in이 없습니다")

        try:
            expires_seconds = int(expires_in)
        except (TypeError, ValueError) as exc:
            raise ValueError("expires_in은 정수여야 합니다") from exc

        now = self.clock()
        return KISToken(
            access_token=access_token,
            token_type=str(raw.get("token_type", "Bearer")),
            expires_at=now + timedelta(seconds=expires_seconds),
        )
