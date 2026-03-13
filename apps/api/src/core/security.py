from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from src.core.config import settings


@dataclass
class Principal:
    subject: str
    token: str
    roles: tuple[str, ...] = ()


async def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    """Very small auth shim.

    - If AUTH_MODE=none, we accept anonymous requests.
    - If AUTH_MODE=jwt, plug in your JWT verification (public key, issuer, audience).
    """

    auth_mode = (settings.auth_mode or "none").lower()
    if auth_mode == "none":
        return Principal(subject="anonymous", token="")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )

    token = authorization.split(" ", 1)[1].strip()

    # TODO: verify JWT signature + claims. Keep intentionally minimal here.
    if auth_mode == "jwt":
        # Replace with jose/pyjwt verification in real implementation.
        return Principal(subject="user", token=token, roles=("user",))

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unsupported AUTH_MODE",
    )
