from datetime import datetime, timedelta, timezone

import pytest

from trading_bot.clients.kis_auth import KISAuthClient, KISAuthConfig, KISToken


def test_config_from_env_requires_key_and_secret(monkeypatch):
    monkeypatch.delenv("KIS_APP_KEY", raising=False)
    monkeypatch.delenv("KIS_APP_SECRET", raising=False)

    with pytest.raises(ValueError):
        KISAuthConfig.from_env()


def test_returns_cached_token_without_refresh():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    calls = {"count": 0}

    def fetch(_):
        calls["count"] += 1
        return {"access_token": "new-token", "expires_in": 3600}

    class FixedStore:
        def load(self):
            return KISToken(
                access_token="cached-token",
                expires_at=now + timedelta(minutes=10),
            )

        def save(self, _token):
            raise AssertionError("save should not be called for valid cached token")

    client = KISAuthClient(
        config=KISAuthConfig("a", "b", "https://example.com"),
        fetch_token=fetch,
        token_store=FixedStore(),
        clock=lambda: now,
    )

    token = client.get_access_token()

    assert token == "cached-token"
    assert calls["count"] == 0


def test_fetches_and_caches_when_missing_or_expired():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    saved = {"token": None}

    def fetch(_):
        return {"access_token": "fresh", "expires_in": 120}

    class EmptyStore:
        def load(self):
            return None

        def save(self, token):
            saved["token"] = token

    client = KISAuthClient(
        config=KISAuthConfig("a", "b", "https://example.com"),
        fetch_token=fetch,
        token_store=EmptyStore(),
        clock=lambda: now,
    )

    token = client.get_access_token()

    assert token == "fresh"
    assert saved["token"] is not None
    assert saved["token"].expires_at == now + timedelta(seconds=120)


def test_force_refresh_ignores_cache():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    calls = {"count": 0}

    def fetch(_):
        calls["count"] += 1
        return {"access_token": "forced", "expires_in": 3600}

    class Store:
        def __init__(self):
            self.saved = None

        def load(self):
            return KISToken(
                access_token="cached-token",
                expires_at=now + timedelta(hours=1),
            )

        def save(self, token):
            self.saved = token

    store = Store()
    client = KISAuthClient(
        config=KISAuthConfig("a", "b", "https://example.com"),
        fetch_token=fetch,
        token_store=store,
        clock=lambda: now,
    )

    token = client.get_access_token(force_refresh=True)

    assert token == "forced"
    assert calls["count"] == 1
    assert store.saved is not None


def test_invalid_response_raises_error():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)

    def fetch(_):
        return {"expires_in": "abc"}

    client = KISAuthClient(
        config=KISAuthConfig("a", "b", "https://example.com"),
        fetch_token=fetch,
        clock=lambda: now,
    )

    with pytest.raises(ValueError):
        client.get_access_token()
