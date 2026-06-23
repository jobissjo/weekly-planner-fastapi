from pymongo import AsyncMongoClient
from beanie import init_beanie
from app.core.settings import setting
from app.models.user import User, TempUserOTP, EmailSetting
from app.models.profile import Profile
from app.models.motivation import Motivation
from app.models.task import Task
from app.models.streak import StreakRule, UserStreak, StreakRewardHistory


async def init_db():
    client = AsyncMongoClient(setting.MONGODB_URL)
    await init_beanie(
        database=client.get_database(),
        document_models=[User, Profile, TempUserOTP, EmailSetting, Motivation, Task, StreakRule, UserStreak, StreakRewardHistory]
    )