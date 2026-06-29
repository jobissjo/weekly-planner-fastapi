from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas import BaseResponse, TokenResponse
from app.schemas.common_schema import RefreshTokenBody
from app.schemas.user_schema import (
    EmailVerifyOtpSchema,
    EmailVerifySchema,
    GoogleLoginSchema,
    LoginEmailSchema,
    RegisterSchema,
)
from app.services import EmailService, UserService

router = APIRouter(prefix="/auth", tags=["Auth"])
email_service = EmailService()
user_service = UserService(email_service=email_service)


@router.post("/verify-email")
async def verify_email(data: EmailVerifySchema) -> BaseResponse[None]:
    await user_service.verify_email(data)
    return BaseResponse(status="success", message="OTP sent successfully", data=None)


@router.post("/verify-email-otp")
async def verify_email_otp(data: EmailVerifyOtpSchema) -> BaseResponse[None]:
    await user_service.verify_email_otp(data)
    return BaseResponse(
        status="success", message="Email verified successfully", data=None
    )


@router.post("/register")
async def register(data: RegisterSchema) -> BaseResponse[None]:
    _user = await user_service.register_user(data)
    return BaseResponse(
        status="success", message="User registered successfully", data=None
    )


@router.post("/login")
async def login(data: LoginEmailSchema) -> BaseResponse[TokenResponse]:
    token_data = await user_service.login_user(data)
    return BaseResponse(
        status="success",
        message="User logged in successfully",
        data=TokenResponse(**token_data),
    )


@router.post("/google")
async def google_login(data: GoogleLoginSchema) -> BaseResponse[TokenResponse]:
    token_data = await user_service.login_or_register_google(data.credential)
    return BaseResponse(
        status="success",
        message="User logged in via Google successfully",
        data=TokenResponse(**token_data),
    )


@router.post("/token")
async def token(
    data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    token_data = await user_service.login_user(
        LoginEmailSchema(email=data.username, password=data.password)
    )
    return TokenResponse(**token_data)


@router.post("/refresh")
async def refresh(
    data: RefreshTokenBody,
) -> TokenResponse:
    token_data = await user_service.refresh_to_access_token(data)
    return TokenResponse(**token_data)
