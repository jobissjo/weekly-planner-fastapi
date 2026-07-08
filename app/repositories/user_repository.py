from beanie import PydanticObjectId

from app.models.profile import Profile
from app.models.user import TempUserOTP, User
from app.utils.common import generate_otp


class UserRepository:
    @staticmethod
    async def get_user_by_email(email: str) -> User:
        return await User.find_one(User.email == email)

    @staticmethod
    async def get_user_by_id(user_id: str) -> User:
        return await User.get(PydanticObjectId(user_id), fetch_links=True)

    @staticmethod
    async def get_user_profile_by_id(user_id: str) -> Profile:
        return await Profile.find_one(Profile.user.id == PydanticObjectId(user_id))

    @staticmethod
    async def get_otp_by_email(email: str) -> TempUserOTP:
        return await TempUserOTP.find_one(TempUserOTP.email == email)

    @staticmethod
    async def create_user_otp(email: str) -> TempUserOTP:
        otp = await generate_otp()
        existing_otp = await UserRepository.get_otp_by_email(email)
        if existing_otp:
            await existing_otp.delete()
        user_otp = TempUserOTP(email=email, otp=otp)
        await user_otp.insert()
        return user_otp

    @staticmethod
    async def update_profile(
        user_id: str,
        bio: str | None,
        profile_picture_url: str | None,
    ) -> Profile:
        profile = await UserRepository.get_user_profile_by_id(user_id)

        if not profile:
            profile = Profile(user=await User.get(PydanticObjectId(user_id)))

        if bio is not None:
            profile.bio = bio

        if profile_picture_url is not None:
            profile.profile_picture_url = profile_picture_url

        await profile.save()
        return profile

    @staticmethod
    async def update_notification_preferences(
        user_id: str,
        email_notifications: bool,
        reminders: bool,
    ) -> Profile:
        profile = await UserRepository.get_user_profile_by_id(user_id)

        if not profile:
            user = await UserRepository.get_user_by_id(user_id)
            profile = Profile(user=user)
            await profile.insert()

        profile.email_notifications = email_notifications
        profile.reminders = reminders

        await profile.save()
        return profile

    @staticmethod
    async def get_users_by_name(name: str) -> list[User]:
        import re

        regx = re.compile(rf".*{re.escape(name)}.*", re.IGNORECASE)
        return await User.find(
            {"$or": [{"first_name": regx}, {"last_name": regx}, {"email": regx}]}
        ).to_list()
