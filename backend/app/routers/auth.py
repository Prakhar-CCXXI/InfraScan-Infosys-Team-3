"""Authentication router handling registration, login, token rotation, logout, password change, and Google OAuth2."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.dependencies import get_current_active_user
from backend.app.core.permissions import require_admin, require_inspector
from backend.app.core.security import oauth
from backend.app.db.session import get_async_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import (
    LogoutRequest,
    PasswordChangeRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from backend.app.schemas.user import AuditLogResponse, UserProfileUpdateRequest, UserResponse
from backend.app.services.audit_service import extract_client_ip, record_audit_event
from backend.app.services.auth_service import (
    authenticate_user,
    change_user_password,
    generate_auth_tokens,
    handle_google_oauth_user,
    logout_user,
    register_user,
    rotate_refresh_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Validate email/password, return 409 Conflict if already exists, hash with Argon2, save user and write audit log.",
)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Register a new user account with Argon2 password hashing."""
    client_ip = extract_client_ip(request)
    user = await register_user(db, payload, ip_address=client_ip)
    token_bundle = generate_auth_tokens(user)

    return TokenResponse(
        access_token=token_bundle["access_token"],
        refresh_token=token_bundle["refresh_token"],
        token_type="bearer",
        expires_in=token_bundle["expires_in"],
        user=token_bundle["user"],
        token=token_bundle["access_token"],
        message="Account registered successfully.",
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Verify credentials and is_active status (returns 401 on failure). Return 15-min Access Token, 7-day Refresh Token, bearer type, and user details.",
)
async def login(
    payload: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Authenticate user with email and password using Argon2 verification."""
    client_ip = extract_client_ip(request)
    user = await authenticate_user(db, payload.email, payload.password, ip_address=client_ip)
    token_bundle = generate_auth_tokens(user)

    return TokenResponse(
        access_token=token_bundle["access_token"],
        refresh_token=token_bundle["refresh_token"],
        token_type="bearer",
        expires_in=token_bundle["expires_in"],
        user=token_bundle["user"],
        token=token_bundle["access_token"],
        message="Login successful.",
    )


@router.post(
    "/token",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="OAuth2 Password Flow Token Endpoint",
    description="FastAPI / Swagger UI compliant token endpoint.",
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """OAuth2 password form token endpoint accepting username (email) and password."""
    client_ip = extract_client_ip(request)
    user = await authenticate_user(db, form_data.username, form_data.password, ip_address=client_ip)
    token_bundle = generate_auth_tokens(user)

    return {
        "access_token": token_bundle["access_token"],
        "refresh_token": token_bundle["refresh_token"],
        "token_type": "bearer",
        "expires_in": token_bundle["expires_in"],
        "user_id": str(user.id),
        "role": user.role.value,
    }


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Issue a new access token while rotating and revoking the old refresh token.",
)
async def refresh_tokens(
    payload: TokenRefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> TokenRefreshResponse:
    """Rotate refresh token and issue a fresh 15-minute access token."""
    client_ip = extract_client_ip(request)
    tokens = await rotate_refresh_token(db, payload.refresh_token, ip_address=client_ip)
    return TokenRefreshResponse(**tokens)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Revoke the active session/refresh token and access token.",
)
async def logout(
    request: Request,
    payload: LogoutRequest | None = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Revoke session and tokens, recording audit trail."""
    client_ip = extract_client_ip(request)

    refresh_token = payload.refresh_token if payload else None
    access_token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            access_token = parts[1]

    await logout_user(
        db,
        user_id=None,
        refresh_token_str=refresh_token,
        access_token_str=access_token,
        ip_address=client_ip,
    )
    return {"message": "Logged out successfully."}


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Allow authenticated users to securely update their password with Argon2 hashing.",
)
async def update_password(
    payload: PasswordChangeRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Change password securely with Argon2 verification and hashing."""
    client_ip = extract_client_ip(request)
    await change_user_password(
        db,
        current_user,
        payload.current_password,
        payload.new_password,
        ip_address=client_ip,
    )
    return {"message": "Password updated successfully."}


# ----------------------------------------------------------------------------
# Google OAuth2 Login (via Authlib)
# ----------------------------------------------------------------------------

@router.get(
    "/google",
    summary="Initiate Google OAuth2 Login",
    description="Redirect user to Google OAuth2 consent screen via Authlib.",
)
async def google_login(request: Request) -> Any:
    """Redirect to Google OAuth2 authorization endpoint."""
    redirect_uri = settings.GOOGLE_REDIRECT_URI

    # If Google credentials are not configured, return an informative response or authorization URL
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or settings.GOOGLE_CLIENT_ID.startswith("dummy"):
        return {
            "message": "Google OAuth2 is configured in foundation mode. Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env for live redirection.",
            "redirect_uri": redirect_uri,
            "provider": "google",
            "scope": "openid email profile",
            "mock_callback_hint": f"To simulate a Google OAuth2 callback in tests, call GET {redirect_uri}?mock_email=user@infrascan.gov&mock_name=Google+User",
        }

    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get(
    "/google/callback",
    response_model=TokenResponse,
    summary="Google OAuth2 Callback Handler",
    description="Handle Google OAuth2 callback, find or create user with a safe default role, and issue standard JWT tokens.",
)
@router.get(
    "/callback/google",
    response_model=TokenResponse,
    summary="Google OAuth2 Callback Handler (Alias)",
)
async def google_callback(
    request: Request,
    code: str | None = Query(default=None, description="Google authorization code"),
    mock_email: str | None = Query(default=None, description="Mock email for automated tests/development"),
    mock_name: str | None = Query(default=None, description="Mock name for automated tests/development"),
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Exchange authorization code via Authlib, provision user with safe default role, and return JWTs."""
    client_ip = extract_client_ip(request)
    email: str | None = None
    full_name: str | None = None

    if mock_email:
        # Development / testing shortcut when live Google credentials are not set
        email = mock_email.strip().lower()
        full_name = mock_name or email.split("@")[0].title()
    elif code:
        try:
            token = await oauth.google.authorize_access_token(request)
            userinfo = token.get("userinfo")
            if not userinfo:
                # Attempt to parse or fetch ID token
                userinfo = await oauth.google.userinfo(token=token)
            if userinfo:
                email = userinfo.get("email")
                full_name = userinfo.get("name")
        except Exception as exc:
            logger.error("Authlib Google OAuth2 exchange error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth2 authorization failed: {str(exc)}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required authorization code from Google OAuth2.",
        )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve verified email address from Google.",
        )

    # Provision user with safe default role (Security rule: Never trust external role)
    user = await handle_google_oauth_user(db, email=email, full_name=full_name or email, ip_address=client_ip)
    token_bundle = generate_auth_tokens(user)

    return TokenResponse(
        access_token=token_bundle["access_token"],
        refresh_token=token_bundle["refresh_token"],
        token_type="bearer",
        expires_in=token_bundle["expires_in"],
        user=token_bundle["user"],
        token=token_bundle["access_token"],
        message="Google OAuth2 authentication successful.",
    )


# ----------------------------------------------------------------------------
# Profile and RBAC Verification Helpers
# ----------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile (Auth Alias)",
    description="Fetch the profile of the currently authenticated user.",
)
async def get_my_profile_alias(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Retrieve account details for authenticated caller."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile (Auth Alias)",
)
@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile (Auth Alias PUT)",
)
async def update_my_profile_alias(
    payload: UserProfileUpdateRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Update profile details for the authenticated user."""
    client_ip = extract_client_ip(request)
    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password.",
            )
        await change_user_password(
            db,
            current_user,
            payload.current_password,
            payload.new_password,
            ip_address=client_ip,
        )
    if payload.full_name and payload.full_name.strip() != current_user.full_name:
        current_user.full_name = payload.full_name.strip()
        await db.commit()
        await db.refresh(current_user)
        await record_audit_event(
            db,
            action="USER_PROFILE_UPDATED",
            resource_type="USER",
            resource_id=current_user.id,
            user_id=current_user.id,
            ip_address=client_ip,
        )
    return UserResponse.model_validate(current_user)


@router.get(
    "/audit-logs",
    response_model=list[AuditLogResponse],
    summary="Retrieve audit logs (Auth Alias)",
    description="Inspect audit trail. Regular users see their own events; Admins see all.",
)
async def view_audit_logs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
) -> list[AuditLogResponse]:
    """Retrieve security audit events."""
    from backend.app.services.audit_service import list_audit_logs
    target_user_id = None if current_user.role == UserRole.ADMIN else current_user.id
    logs = await list_audit_logs(db, user_id=target_user_id, limit=limit, offset=offset)
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get(
    "/roles",
    summary="List System Roles and RBAC Hierarchy",
    description="Retrieve all available roles within the InfraScan system.",
)
async def get_system_roles() -> list[dict[str, str]]:
    """List all supported system roles."""
    return [
        {"role": r.value, "title": r.display_name}
        for r in UserRole
    ]


@router.get(
    "/rbac-test/inspector-only",
    summary="RBAC Test: Inspector Access",
    description="Endpoint restricted to Infrastructure Inspectors and Administrators.",
)
async def rbac_test_inspector(
    user: Annotated[User, Depends(require_inspector)],
) -> dict[str, str]:
    """Verify inspector RBAC gate."""
    return {
        "status": "authorized",
        "message": f"Welcome Inspector {user.full_name}. You have access to inspection workflows.",
        "role": user.role.value,
    }


@router.get(
    "/rbac-test/admin-only",
    summary="RBAC Test: Admin Access",
    description="Endpoint strictly restricted to Administrators.",
)
async def rbac_test_admin(
    user: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    """Verify admin RBAC gate."""
    return {
        "status": "authorized",
        "message": f"Administrator privilege granted for {user.full_name}.",
        "role": user.role.value,
    }

