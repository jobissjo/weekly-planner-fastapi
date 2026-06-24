import asyncio
from app.core.db_config import init_db
from app.models.user import User
from app.models.profile import Profile
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.core.security import hash_password
from beanie import PydanticObjectId


async def main():
    # Rebuild profile model with User namespace BEFORE init_db
    Profile.model_rebuild(_types_namespace={"User": User})

    print("Initializing DB...")
    await init_db()

    email = "testsettings@demo.com"
    u = await User.find_one(User.email == email)
    if u:
        profile = await UserRepository.get_user_profile_by_id(str(u.id))
        if profile:
            await profile.delete()
        await u.delete()

    print("Creating test user...")
    password_hash = await hash_password("oldpassword")
    user = User(
        email=email,
        password=password_hash,
        first_name="Test",
        last_name="User",
        role="user",
        is_active=True,
    )
    await user.insert()
    print(f"User created: {user.email}")

    # Fetch user and create profile
    db_user = await User.get(user.id)
    profile = Profile(user=db_user)
    await profile.insert()

    # Get raw dictionary from MongoDB for the inserted profile
    raw_profile = await Profile.get_pymongo_collection().find_one({"_id": profile.id})
    print(f"Raw profile doc in MongoDB: {raw_profile}")

    # Try querying using get_user_profile_by_id
    q = await UserRepository.get_user_profile_by_id(str(user.id))
    print(f"Query (get_user_profile_by_id): {q}")

    service = UserService(None)

    # 1. Change password
    print("Testing change password...")
    await service.change_password(str(user.id), "oldpassword", "newpassword")
    print("Password changed successfully!")

    # Verify we can't change password with wrong old password
    try:
        await service.change_password(str(user.id), "wrongpassword", "anothernew")
        print("ERROR: Allowed password change with incorrect current password!")
    except Exception as e:
        print(f"Success: Password change failed as expected: {e.message}")

    # 2. Update notification preferences
    print("Testing update notification preferences...")
    await service.update_notification_preferences(str(user.id), False, False)

    # Reload and verify
    updated_profile = await UserRepository.get_user_profile_by_id(str(user.id))
    print(
        f"Updated Prefs: Email={updated_profile.email_notifications}, Reminders={updated_profile.reminders}"
    )
    assert updated_profile.email_notifications is False
    assert updated_profile.reminders is False

    # Cleanup
    await updated_profile.delete()
    u_del = await User.get(user.id)
    if u_del:
        await u_del.delete()
    print("All profile/settings tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
