from typing import List, Optional

from beanie import PydanticObjectId

from app.models.streak import StreakRewardHistory, StreakRule, UserStreak


class StreakRepository:
    # --- StreakRule methods ---

    @staticmethod
    async def get_active_streak_rule() -> Optional[StreakRule]:
        return await StreakRule.find_one(StreakRule.is_active == True)

    @staticmethod
    async def get_streak_rule_by_id(rule_id: str) -> Optional[StreakRule]:
        try:
            return await StreakRule.get(PydanticObjectId(rule_id))
        except Exception:
            return None

    @staticmethod
    async def list_all_streak_rules() -> List[StreakRule]:
        return await StreakRule.find_all().sort("-created_at").to_list()

    @staticmethod
    async def create_streak_rule(
        name: str,
        required_consecutive_days: int,
        freezes_to_grant: int,
        max_freezes_allowed: int,
        is_active: bool = True,
    ) -> StreakRule:
        rule = StreakRule(
            name=name,
            required_consecutive_days=required_consecutive_days,
            freezes_to_grant=freezes_to_grant,
            max_freezes_allowed=max_freezes_allowed,
            is_active=is_active,
        )
        await rule.insert()
        return rule

    @staticmethod
    async def delete_streak_rule(rule_id: str) -> bool:
        rule = await StreakRepository.get_streak_rule_by_id(rule_id)
        if not rule:
            return False
        await rule.delete()
        return True

    # --- UserStreak methods ---

    @staticmethod
    async def get_user_streak(user_id: PydanticObjectId) -> Optional[UserStreak]:
        return await UserStreak.find_one(UserStreak.user_id == user_id)

    @staticmethod
    async def create_user_streak(
        user_id: PydanticObjectId,
        current_streak: int = 0,
        longest_streak: int = 0,
        available_freezes: int = 0,
        last_completed_date: Optional[str] = None,
        last_rewarded_streak: int = 0,
    ) -> UserStreak:
        user_streak = UserStreak(
            user_id=user_id,
            current_streak=current_streak,
            longest_streak=longest_streak,
            available_freezes=available_freezes,
            last_completed_date=last_completed_date,
            last_rewarded_streak=last_rewarded_streak,
        )
        await user_streak.insert()
        return user_streak

    # --- StreakRewardHistory methods ---

    @staticmethod
    async def list_reward_history(
        user_id: PydanticObjectId,
    ) -> List[StreakRewardHistory]:
        return (
            await StreakRewardHistory.find(StreakRewardHistory.user_id == user_id)
            .sort("-created_at")
            .to_list()
        )

    @staticmethod
    async def create_reward_history(
        user_id: PydanticObjectId,
        rule_id: Optional[PydanticObjectId],
        freezes_granted: int,
        streak_at_reward: int,
    ) -> StreakRewardHistory:
        history = StreakRewardHistory(
            user_id=user_id,
            rule_id=rule_id,
            freezes_granted=freezes_granted,
            streak_at_reward=streak_at_reward,
        )
        await history.insert()
        return history
