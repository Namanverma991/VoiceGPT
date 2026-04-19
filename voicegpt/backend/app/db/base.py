"""
SQLAlchemy model imports — ensures all models are registered with Base.
"""

from app.db.session import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.chat import ChatSession, ChatMessage  # noqa: F401
