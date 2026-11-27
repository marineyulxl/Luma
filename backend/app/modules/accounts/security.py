"""密码验证、JWT 与有容量上限的单进程请求限流。"""

import hashlib
import math
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import HashVerificationError, UnknownHashError

from app.core.config import Settings

COOKIE_NAME = "luma_refresh"
COOKIE_PATH = "/api/auth/sessions"


class AuthError(Exception):
    def __init__(
        self,
        code: str = "unauthenticated",
        message: str = "登录状态已失效",
        status: int = 401,
        retry_after: int | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status = status
        self.retry_after = retry_after
        super().__init__(message)


@dataclass(frozen=True)
class AccessIdentity:
    owner_id: UUID
    session_id: UUID


class TokenSecurity:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.passwords = PasswordHash.recommended()
        # 不存在的账号也执行同样的哈希校验，减少账号存在性时序差异。
        self.dummy_hash = self.passwords.hash(secrets.token_urlsafe(32))

    def verify_password(self, password: str, encoded: str | None) -> bool:
        try:
            valid = self.passwords.verify(password, encoded or self.dummy_hash)
        except (ValueError, UnknownHashError, HashVerificationError):
            return False
        return valid and encoded is not None

    def encode(
        self, owner_id: UUID, session_id: UUID, now: datetime, deadline: datetime
    ) -> tuple[str, int]:
        issued = int(now.timestamp())
        expiry = min(issued + self.settings.access_token_seconds, int(deadline.timestamp()))
        if expiry <= issued:
            raise AuthError()
        token = jwt.encode(
            {
                "sub": str(owner_id),
                "sid": str(session_id),
                "iat": issued,
                "exp": expiry,
                "iss": self.settings.auth_issuer,
                "aud": self.settings.auth_audience,
                "type": "access",
            },
            self.settings.auth_signing_key.get_secret_value(),
            algorithm="HS256",
        )
        return token, expiry - issued

    def decode(self, token: str) -> AccessIdentity:
        if len(token) > 4096:
            raise AuthError()
        try:
            claims = jwt.decode(
                token,
                self.settings.auth_signing_key.get_secret_value(),
                algorithms=["HS256"],
                issuer=self.settings.auth_issuer,
                audience=self.settings.auth_audience,
                options={"require": ["sub", "sid", "iat", "exp", "iss", "aud", "type"]},
            )
            if claims["type"] != "access":
                raise AuthError()
            return AccessIdentity(UUID(claims["sub"]), UUID(claims["sid"]))
        except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
            raise AuthError() from None


def refresh_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class RequestLimiter:
    """仅使用直接连接 IP，不信任客户端 X-Forwarded-For。"""

    def __init__(self) -> None:
        self.entries: OrderedDict[tuple[str, str], tuple[float, int]] = OrderedDict()
        self.lock = Lock()

    def check(self, scope: str, address: str, limit: int, seconds: int) -> None:
        now = time.monotonic()
        with self.lock:
            key = (scope, address)
            start, count = self.entries.get(key, (now, 0))
            if now - start >= seconds:
                start, count = now, 0
            self.entries[key] = (start, count + 1)
            self.entries.move_to_end(key)
            while len(self.entries) > 4096:
                self.entries.popitem(last=False)
            if count >= limit:
                raise AuthError(
                    "rate_limited",
                    "请求过于频繁，请稍后再试",
                    429,
                    max(1, math.ceil(seconds - (now - start))),
                )
