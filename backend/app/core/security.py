"""Security, authentication, and role authorization placeholders.

Full Supabase JWT verification and role dependencies will be wired in Phase 2
once the Supabase schema and auth keys are confirmed.
"""

from typing import List, Optional
from fastapi import Header, HTTPException, status
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """Representing an authenticated user session."""

    user_id: str
    roles: List[str]
    village_id: Optional[str] = None


async def get_current_user_placeholder(
    authorization: Optional[str] = Header(None),
) -> Optional[AuthenticatedUser]:
    """Placeholder dependency for extracting the authenticated user.

    In Phase 2, this dependency will validate Supabase JWT tokens and extract
    user roles and village assignments.
    """
    if not authorization:
        # For public endpoints, user is None
        return None

    # Placeholder logic for Phase 0/1 scaffolding
    return AuthenticatedUser(
        user_id="placeholder-user-id",
        roles=["resident"],
        village_id=None,
    )
