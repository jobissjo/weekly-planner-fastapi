from datetime import datetime, timedelta, timezone

import httpx
from beanie import PydanticObjectId

from app.core.logger_config import logger as default_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.core.settings import setting
from app.models import Profile, TempUserOTP, User
from app.models.enums import UserRole
from app.repositories import UserRepository
from app.schemas import user_schema
from app.schemas.common_schema import RefreshTokenBody

# render_email_template, send_email
from app.services.common_service import CommonService
from app.services.email_service import EmailService
from app.utils.common import CustomException

PROFILE_UPLOAD_FOLDER = "profile"


class UserService:
    def __init__(self, email_service: EmailService, logger=None):
        self.email_service = email_service
        self.logger = logger or default_logger

    async def register_user(self, user_data: user_schema.RegisterSchema):
        otp = await self.get_user_otp(user_data.email)
        if otp.otp != user_data.otp:
            raise CustomException("Invalid OTP", 400)

        existing_user = await UserRepository.get_user_by_email(user_data.email)

        if existing_user and existing_user.is_active:
            raise CustomException(
                "A user with this username or email already exists.", 400
            )

        ref_code = user_data.referral_code.strip() if user_data.referral_code else None
        user_dict = user_data.model_dump(exclude={"otp", "referral_code"})
        hashed_password = await hash_password(user_dict["password"])

        initial_xp = 450 if ref_code else 350

        if not existing_user:
            user_dict["password"] = hashed_password
            user = User(**user_dict)
            await user.insert()

            my_ref_code = f"ZEN-{user.first_name.upper().replace(' ', '')}2026"
            profile = Profile(
                user=user,
                xp=initial_xp,
                level=(initial_xp // 500) + 1,
                referral_code=my_ref_code,
                referred_by=ref_code,
                accountability_partners=[],
            )

            if ref_code:
                referrer_profile = await Profile.find_one(Profile.referral_code == ref_code)
                if referrer_profile:
                    referrer_profile.xp += 250
                    referrer_profile.level = (referrer_profile.xp // 500) + 1

                    new_user_name = f"{user.first_name} {user.last_name}".strip()
                    if new_user_name not in referrer_profile.accountability_partners:
                        referrer_profile.accountability_partners.append(new_user_name)
                    await referrer_profile.save()

                    referrer_user = await User.get(referrer_profile.user.id)
                    if referrer_user:
                        ref_name = f"{referrer_user.first_name} {referrer_user.last_name}".strip()
                        profile.accountability_partners.append(ref_name)

            await profile.insert()
            return user

        elif not existing_user.is_active and existing_user.email == user_data.email:
            existing_user.password = hashed_password
            existing_user.role = user_data.role
            existing_user.is_active = True
            await existing_user.save()
            return existing_user

        raise CustomException("A user with this username already exists.", 400)


    async def login_user(self, user_data: user_schema.LoginEmailSchema):
        existing_user = await UserRepository.get_user_by_email(user_data.email)
        if not existing_user:
            raise CustomException("email not exists", 400)

        if not existing_user.password or not getattr(
            existing_user, "allow_password_login", True
        ):
            raise CustomException(
                "This account is configured for Google Sign-In. Please log in using Google.",
                400,
            )

        if not await verify_password(user_data.password, existing_user.password):
            raise CustomException("Invalid credentials.", 401)

        access_token = await create_access_token({"user_id": str(existing_user.id)})
        refresh_token = await create_refresh_token({"user_id": str(existing_user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "role": existing_user.role,
            "user": {
                "email": existing_user.email,
                "first_name": existing_user.first_name,
                "last_name": existing_user.last_name,
                "role": existing_user.role.value,
                "google_id": existing_user.google_id,
                "allow_password_login": getattr(
                    existing_user, "allow_password_login", True
                ),
                "has_password": existing_user.password is not None,
            },
        }

    async def login_or_register_google(self, credential_token: str):
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={credential_token}"
                )
            except Exception:
                raise CustomException("Failed to verify token with Google API.", 400)

            if resp.status_code != 200:
                raise CustomException("Invalid Google token.", 400)

            payload = resp.json()

        if setting.GOOGLE_CLIENT_ID and payload.get("aud") != setting.GOOGLE_CLIENT_ID:
            raise CustomException("Google token audience mismatch.", 400)

        email = payload.get("email")
        google_id = payload.get("sub")
        first_name = payload.get("given_name") or payload.get("name", "Google")
        last_name = payload.get("family_name") or "User"

        if not email:
            raise CustomException("Email not provided by Google.", 400)

        existing_user = await UserRepository.get_user_by_email(email)

        if existing_user:
            if not getattr(existing_user, "google_id", None):
                existing_user.google_id = google_id
                await existing_user.save()
            if not existing_user.is_active:
                existing_user.is_active = True
                await existing_user.save()
        else:
            existing_user = User(
                email=email,
                password=None,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.USER,
                is_active=True,
                google_id=google_id,
                allow_password_login=False,
            )
            await existing_user.insert()

        access_token = await create_access_token({"user_id": str(existing_user.id)})
        refresh_token = await create_refresh_token({"user_id": str(existing_user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "role": existing_user.role,
            "user": {
                "email": existing_user.email,
                "first_name": existing_user.first_name,
                "last_name": existing_user.last_name,
                "role": existing_user.role.value
                if hasattr(existing_user.role, "value")
                else str(existing_user.role),
                "google_id": existing_user.google_id,
                "allow_password_login": getattr(
                    existing_user, "allow_password_login", True
                ),
                "has_password": existing_user.password is not None,
            },
        }

    async def verify_email(self, data: user_schema.EmailVerifySchema):
        user = await UserRepository.get_user_by_email(data.email)
        if user and user.is_active:
            raise CustomException("Email already exists", 400)

        user_otp = await UserRepository.create_user_otp(data.email)
        await self.email_service.send_email(
            recipient=data.email,
            subject="Verify Your Account",
            template_name="email/verify_account.html",
            template_data={"otp": user_otp.otp, "name": data.first_name},
            use_admin_email=True,
        )

    async def verify_email_otp(self, data: user_schema.EmailVerifyOtpSchema):
        existing_user = await UserRepository.get_user_by_email(data.email)
        if existing_user and existing_user.is_active:
            raise CustomException("Email already exists", 400)

        user_otp = await self.get_user_otp(data.email)
        if user_otp.otp != data.otp:
            raise CustomException("Invalid OTP", 400)

    async def refresh_to_access_token(self, token_data: RefreshTokenBody):
        payload = await verify_refresh_token(token_data.refresh_token)
        user_id = payload.get("user_id")

        if not user_id:
            raise CustomException("Invalid refresh token", 401)

        user = await UserRepository.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise CustomException("User not found or inactive", 401)

        access_token = await create_access_token({"user_id": str(user.id)})
        refresh_token = await create_refresh_token({"user_id": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "role": user.role,
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.value,
                "google_id": user.google_id,
                "allow_password_login": getattr(user, "allow_password_login", True),
                "has_password": user.password is not None,
            },
        }

    # Delegated from OTP service:
    async def get_user_otp(self, email: str) -> TempUserOTP:
        otp = await UserRepository.get_otp_by_email(email)
        if otp is None:
            raise CustomException("OTP not found", 400)

        created_at = (
            otp.created_at.replace(tzinfo=timezone.utc)
            if otp.created_at.tzinfo is None
            else otp.created_at
        )
        if created_at < datetime.now(timezone.utc) - timedelta(minutes=5):
            await self.delete_user_otp(email)
            raise CustomException("OTP expired", 400)

        return otp

    async def delete_user_otp(self, email: str):
        otp = await UserRepository.get_otp_by_email(email)
        if otp:
            await otp.delete()

    async def update_profile(
        self, user_id: str, data: user_schema.ProfileUpdateSchema
    ) -> Profile:
        profile_picture_url = (
            await CommonService.save_base64_file(
                data.profile_picture, PROFILE_UPLOAD_FOLDER
            )
            if data.profile_picture
            else None
        )

        return await UserRepository.update_profile(
            user_id=user_id,
            bio=data.bio,
            profile_picture_url=profile_picture_url,
        )

    async def update_profile_form(
        self, user_id: str, data: user_schema.ProfileUpdateForm
    ) -> Profile:
        profile_picture_url = (
            await CommonService.save_upload_file(
                data.profile_picture, PROFILE_UPLOAD_FOLDER
            )
            if data.profile_picture
            else None
        )
        return await UserRepository.update_profile(
            user_id=user_id,
            bio=data.bio,
            profile_picture_url=profile_picture_url,
        )

    async def change_password(self, user_id: str, old_password: str, new_password: str):
        user = await UserRepository.get_user_by_id(user_id)
        if not user:
            raise CustomException("User not found", 404)

        if user.password:
            if not old_password or not await verify_password(
                old_password, user.password
            ):
                raise CustomException("Incorrect current password", 400)

        user.password = await hash_password(new_password)
        user.allow_password_login = True
        await user.save()

    async def update_notification_preferences(
        self, user_id: str, email_notifications: bool, reminders: bool
    ):
        await UserRepository.update_notification_preferences(
            user_id, email_notifications, reminders
        )

    async def update_auth_settings(self, user_id: str, allow_password_login: bool):
        user = await UserRepository.get_user_by_id(user_id)
        if not user:
            raise CustomException("User not found", 404)

        if allow_password_login and not user.password:
            raise CustomException(
                "You must set a password before enabling email and password login.",
                400,
            )

        user.allow_password_login = allow_password_login
        await user.save()

    async def register_push_token(self, user_id: str, push_token: str):
        user = await User.get(PydanticObjectId(user_id))
        if not user:
            raise CustomException("User not found", 404)
        if not getattr(user, "push_tokens", None):
            user.push_tokens = []
        if push_token not in user.push_tokens:
            user.push_tokens.append(push_token)
            await user.save()

    async def unregister_push_token(self, user_id: str, push_token: str):
        user = await User.get(PydanticObjectId(user_id))
        if not user:
            raise CustomException("User not found", 404)
        if getattr(user, "push_tokens", None) and push_token in user.push_tokens:
            user.push_tokens.remove(push_token)
            await user.save()


class TempUserOTPService:
    @staticmethod
    async def get_user_otp(email: str) -> TempUserOTP:
        otp = await UserRepository.get_otp_by_email(email)
        if otp is None:
            raise CustomException(message="Otp not found", status_code=400)
        created_at = otp.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at < datetime.now(timezone.utc) - timedelta(minutes=5):
            await TempUserOTPService.delete_user_otp(email)
            raise CustomException(message="Otp expired", status_code=400)
        return otp

    @staticmethod
    async def delete_user_otp(email: str):
        otp = await UserRepository.get_otp_by_email(email)
        if otp is None:
            raise CustomException(message="Otp not found", status_code=400)
        await otp.delete()
        return {"message": "Otp deleted successfully"}
