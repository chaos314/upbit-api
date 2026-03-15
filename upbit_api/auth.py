from __future__ import annotations

import hashlib
import uuid
from typing import Any, Mapping
from urllib.parse import unquote, urlencode

import jwt


def build_query_string(params: Mapping[str, Any] | None) -> str:
    """
    Build non-url-encoded query string used for Upbit query_hash.

    Upbit requires query_hash to be generated from the non-URL-encoded query string.
    """
    if not params:
        return ""
    return unquote(urlencode(params, doseq=True))


def sha512_hexdigest(text: str) -> str:
    return hashlib.sha512(text.encode("utf-8")).hexdigest()


def create_jwt_token(
    access_key: str,
    secret_key: str,
    query_string: str = "",
    nonce: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "access_key": access_key,
        "nonce": nonce or str(uuid.uuid4()),
    }

    if query_string:
        payload["query_hash"] = sha512_hexdigest(query_string)
        payload["query_hash_alg"] = "SHA512"

    token = jwt.encode(payload, secret_key, algorithm="HS512")
    return token if isinstance(token, str) else token.decode("utf-8")
