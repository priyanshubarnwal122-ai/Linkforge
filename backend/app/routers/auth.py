"""
app/routers/auth.py — Auth endpoints.
No business logic here — just HTTP: parse request, call service, return response.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import RedirectResponse

from app.deps import CurrentUserId, DbSession
from app.schemas import RefreshRequest, TokenPair, UserCreate, UserLogin, UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )


@router.post("/register", response_model=UserResponse, status_code=201, summary="Create account")
async def register(data: UserCreate, background_tasks: BackgroundTasks, db: DbSession) -> UserResponse:
    user = await AuthService(db).register(data, background_tasks)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenPair, summary="Log in")
async def login(data: UserLogin, request: Request, db: DbSession) -> TokenPair:
    tokens = await AuthService(db).login(data.email, data.password, _client_ip(request))
    return TokenPair(**tokens)


@router.post("/refresh", response_model=TokenPair, summary="Refresh access token")
async def refresh(data: RefreshRequest, db: DbSession) -> TokenPair:
    tokens = await AuthService(db).refresh(data.refresh_token)
    return TokenPair(**tokens)


@router.post("/logout", status_code=204, summary="Log out (revoke refresh token)")
async def logout(data: RefreshRequest, db: DbSession) -> None:
    await AuthService(db).logout(data.refresh_token)


@router.get("/verify-email", summary="Verify email address")
async def verify_email(token: str, db: DbSession) -> dict[str, str]:
    user = await AuthService(db).verify_email(token)
    return {"message": "Email verified successfully.", "email": user.email}


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def me(user_id: CurrentUserId, db: DbSession) -> UserResponse:
    user = await AuthService(db).get_user(user_id)
    return UserResponse.model_validate(user)


@router.get("/google/login", summary="Redirect to Google OAuth login page")
async def google_login() -> RedirectResponse:
    url = AuthService.get_google_auth_url()
    return RedirectResponse(url=url)


@router.get("/google/callback", summary="Google OAuth callback endpoint")
async def google_callback(code: str, db: DbSession) -> RedirectResponse:
    tokens = await AuthService(db).google_login_callback(code)
    return RedirectResponse(url=f"/#access_token={tokens['access_token']}")
