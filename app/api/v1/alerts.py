"""HydroVision alert management API."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.supabase_client import get_supabase_client


router = APIRouter(prefix="/alerts", tags=["Alerts"])

ALLOWED_TIERS = {"Watch", "Warning", "Danger", "Evacuate"}
APPROVER_ROLES = {"officer", "admin"}


# -------------------------------------------------------------------
# Request models
# -------------------------------------------------------------------

class AlertDraft(BaseModel):
    village_code: str = Field(min_length=1, max_length=100)
    tier: str
    edited_message: str | None = Field(default=None, max_length=2000)
    is_simulated: bool = False


class AlertRejection(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

def get_response_meta(request: Request) -> dict:
    """Return standard response metadata."""

    return {
        "request_id": getattr(request.state, "request_id", None),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }



def require_approver(authorization: str | None) -> str:
    """Authenticate a Supabase user and require officer/admin role."""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="A valid Supabase Bearer access token is required.",
        )

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="A valid Supabase Bearer access token is required.",
        )

    client = get_supabase_client()

    # Verify the access token and retrieve the authenticated user.
    try:
        auth_result = client.auth.get_user(token)
        user = auth_result.user
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Supabase access token.",
        )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unauthenticated user.",
        )

    # Check the user's assigned application roles.
    try:
        role_result = (
            client.table("user_roles")
            .select("role")
            .eq("user_id", str(user.id))
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to verify the user's role.",
        )

    user_roles = {
        row.get("role")
        for row in (role_result.data or [])
        if row.get("role")
    }

    if not user_roles.intersection(APPROVER_ROLES):
        raise HTTPException(
            status_code=403,
            detail="Only authorized officers or admins can approve or reject alerts.",
        )

    return str(user.id)



def get_alert_by_id(client, alert_id: UUID) -> dict:
    """Fetch one alert or return 404."""

    result = (
        client.table("alerts")
        .select("*")
        .eq("id", str(alert_id))
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="Alert not found.",
        )

    return result.data[0]


# -------------------------------------------------------------------
# GET /api/v1/alerts
# List alerts, optionally filtered by village and status.
# -------------------------------------------------------------------

@router.get("")
def list_alerts(
    request: Request,
    village_code: str | None = None,
    alert_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
):
    # Public listing must never expose drafts or other unapproved alerts.
    if alert_status and alert_status != "approved":
        raise HTTPException(
            status_code=403,
            detail="Only approved alerts are available on this endpoint.",
        )

    client = get_supabase_client()

    query = (
        client.table("alerts")
        .select("*")
        .eq("status", "approved")
    )

    if village_code:
        village_result = (
            client.table("villages")
            .select("id")
            .eq("code", village_code)
            .limit(1)
            .execute()
        )

        if not village_result.data:
            raise HTTPException(
                status_code=404,
                detail="Village not found.",
            )

        query = query.eq("village_id", village_result.data[0]["id"])

    result = (
        query
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    alerts = result.data or []

    return {
        "data": alerts,
        "meta": {
            **get_response_meta(request),
            "count": len(alerts),
        },
    }
@router.post("", status_code=201)
def create_alert_draft(
    payload: AlertDraft,
    request: Request,
    authorization: str | None = Header(default=None),
):
    
    if payload.tier not in ALLOWED_TIERS:
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid alert tier. Choose Watch, Warning, "
                "Danger, or Evacuate."
            ),
        )
    require_approver(authorization)

    client = get_supabase_client()

    village_result = (
        client.table("villages")
        .select("id, code")
        .eq("code", payload.village_code)
        .limit(1)
        .execute()
    )

    if not village_result.data:
        raise HTTPException(
            status_code=404,
            detail="Village not found.",
        )

    village = village_result.data[0]

    # The database requires the message column to be non-null.
    message = (
        payload.edited_message.strip()
        if payload.edited_message
        and payload.edited_message.strip()
        else f"{payload.tier} alert for village {village['code']}."
    )

    result = (
        client.table("alerts")
        .insert(
            {
                "village_id": village["id"],
                "tier": payload.tier,
                "status": "draft",
                "message": message,
                "edited_message": payload.edited_message,
                "is_simulated": payload.is_simulated,
            }
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="The alert draft could not be created.",
        )

    return {
        "data": result.data[0],
        "meta": get_response_meta(request),
    }


# -------------------------------------------------------------------
# POST /api/v1/alerts/{alert_id}/approve
# Approve a draft as an authorized officer/admin.
# -------------------------------------------------------------------

@router.post("/{alert_id}/approve")
def approve_alert(
    alert_id: UUID,
    request: Request,
    authorization: str | None = Header(default=None),
):
    approver_id = require_approver(authorization)
    client = get_supabase_client()

    alert = get_alert_by_id(client, alert_id)

    if alert.get("status") != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft alerts can be approved.",
        )

    approved_at = datetime.now(timezone.utc).isoformat()

    result = (
        client.table("alerts")
        .update(
            {
                "status": "approved",
                "approved_by": approver_id,
                "approved_at": approved_at,
                "rejection_reason": None,
            }
        )
        .eq("id", str(alert_id))
        .eq("status", "draft")
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=409,
            detail="The alert was not updated. It may no longer be a draft.",
        )

    return {
        "data": result.data[0],
        "meta": get_response_meta(request),
    }


# -------------------------------------------------------------------
# POST /api/v1/alerts/{alert_id}/reject
# Reject a draft as an authorized officer/admin.
# -------------------------------------------------------------------

@router.post("/{alert_id}/reject")
def reject_alert(
    alert_id: UUID,
    payload: AlertRejection,
    request: Request,
    authorization: str | None = Header(default=None),
):
    # Validate the user's identity and authorization before changing data.
    require_approver(authorization)
    client = get_supabase_client()

    alert = get_alert_by_id(client, alert_id)

    if alert.get("status") != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft alerts can be rejected.",
        )

    result = (
        client.table("alerts")
        .update(
            {
                "status": "rejected",
                "rejection_reason": payload.reason.strip(),
            }
        )
        .eq("id", str(alert_id))
        .eq("status", "draft")
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=409,
            detail="The alert was not updated. It may no longer be a draft.",
        )

    return {
        "data": result.data[0],
        "meta": get_response_meta(request),
    }
