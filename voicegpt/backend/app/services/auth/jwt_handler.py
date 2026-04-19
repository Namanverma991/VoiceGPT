"""
JWT Handler — thin wrapper used across auth service.
Re-exports from core.security for clean service-layer imports.
"""

from app.core.security import (  # noqa: F401
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
