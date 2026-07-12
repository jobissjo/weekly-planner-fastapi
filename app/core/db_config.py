from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.core.settings import setting
from app.models.announcement import Announcement
from app.models.feedback import Feedback
from app.models.motivation import Motivation
from app.models.profile import Profile
from app.models.reward import Reward
from app.models.streak import StreakRewardHistory, StreakRule, UserStreak
from app.models.task import Task
from app.models.user import EmailSetting, TempUserOTP, User


async def init_db():
    client = AsyncMongoClient(setting.MONGODB_URL)
    await init_beanie(
        database=client.get_database(),
        document_models=[
            User,
            Profile,
            TempUserOTP,
            EmailSetting,
            Motivation,
            Task,
            StreakRule,
            UserStreak,
            StreakRewardHistory,
            Reward,
            Feedback,
            Announcement,
        ],
    )
