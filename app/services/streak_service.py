from datetime import datetime, timedelta, date
from typing import List, Optional
from beanie import PydanticObjectId
from app.models.streak import StreakRule, UserStreak, StreakRewardHistory
from app.models.task import Task
from app.models.enums import TaskStatus
from app.repositories.streak_repository import StreakRepository
from app.schemas.streak_schema import StreakRuleCreateSchema, StreakRuleUpdateSchema
from app.utils.common import CustomException
from app.core.logger_config import logger as default_logger


class StreakService:

    def __init__(self, logger=None):
        self.logger = logger or default_logger

    # --- StreakRule Admin CRUD ---

    async def create_streak_rule(self, schema: StreakRuleCreateSchema) -> StreakRule:
        # Enforce "only one rule can be active at a time"
        if schema.is_active:
            await self._deactivate_all_rules()

        rule = await StreakRepository.create_streak_rule(
            name=schema.name,
            required_consecutive_days=schema.required_consecutive_days,
            freezes_to_grant=schema.freezes_to_grant,
            max_freezes_allowed=schema.max_freezes_allowed,
            is_active=schema.is_active,
        )
        return rule

    async def get_streak_rule_by_id(self, rule_id: str) -> StreakRule:
        rule = await StreakRepository.get_streak_rule_by_id(rule_id)
        if not rule:
            raise CustomException("Streak rule not found", status_code=404)
        return rule

    async def list_all_streak_rules(self) -> List[StreakRule]:
        return await StreakRepository.list_all_streak_rules()

    async def update_streak_rule(
        self, rule_id: str, schema: StreakRuleUpdateSchema
    ) -> StreakRule:
        rule = await self.get_streak_rule_by_id(rule_id)

        update_data = schema.model_dump(exclude_unset=True)

        if update_data.get("is_active") is True:
            await self._deactivate_all_rules()

        for key, val in update_data.items():
            setattr(rule, key, val)

        rule.updated_at = datetime.utcnow()
        await rule.save()
        return rule

    async def delete_streak_rule(self, rule_id: str) -> None:
        deleted = await StreakRepository.delete_streak_rule(rule_id)
        if not deleted:
            raise CustomException("Streak rule not found", status_code=404)

    async def get_active_streak_rule(self) -> Optional[StreakRule]:
        return await StreakRepository.get_active_streak_rule()

    async def _deactivate_all_rules(self) -> None:
        active_rules = await StreakRule.find(StreakRule.is_active == True).to_list()
        for r in active_rules:
            r.is_active = False
            await r.save()

    # --- User Streak tracking & calculation ---

    async def get_or_update_user_streak(
        self, user_id: PydanticObjectId, today_str: str
    ) -> UserStreak:
        user_streak = await StreakRepository.get_user_streak(user_id)
        if not user_streak:
            user_streak = await StreakRepository.create_user_streak(user_id)
            return user_streak

        if not user_streak.last_completed_date:
            return user_streak

        # Parse dates to calculate missed days
        try:
            last_date = datetime.strptime(user_streak.last_completed_date, "%Y-%m-%d").date()
            current_date = datetime.strptime(today_str, "%Y-%m-%d").date()
        except Exception:
            return user_streak

        diff = (current_date - last_date).days
        if diff <= 1:
            # Completed a task today or yesterday, streak is active
            return user_streak

        # Missed days between last completed date and today
        missed = diff - 1
        if missed <= user_streak.available_freezes:
            # The streak can be preserved by consuming freezes once they complete a task.
            # We temporarily adjust available_freezes for display purposes
            user_streak.available_freezes -= missed
        else:
            # Freezes are insufficient. Streak broke!
            user_streak.current_streak = 0
            user_streak.last_rewarded_streak = 0
            # Keep available_freezes intact (they weren't used since they couldn't save the streak)
            await user_streak.save()

        return user_streak

    async def recalculate_user_streak(self, user_id: PydanticObjectId) -> UserStreak:
        # 1. Fetch unique sorted completed task dates
        completed_tasks = await Task.find(
            Task.user_id == user_id, Task.status == TaskStatus.COMPLETED
        ).to_list()
        completed_dates = sorted(list(set(t.date for t in completed_tasks)))

        # 2. Get active rule configurations
        active_rule = await self.get_active_streak_rule()

        # 3. Fetch or create user streak
        user_streak = await StreakRepository.get_user_streak(user_id)
        if not user_streak:
            user_streak = await StreakRepository.create_user_streak(user_id)

        # 4. Simulate timeline
        current_streak = 0
        longest_streak = 0
        available_freezes = 0
        last_rewarded_streak = 0
        last_completed_date: Optional[date] = None

        # Recreate reward history logs
        # First, clear existing reward history for this user
        existing_rewards = await StreakRewardHistory.find(
            StreakRewardHistory.user_id == user_id
        ).to_list()
        for r in existing_rewards:
            await r.delete()

        for date_str in completed_dates:
            try:
                curr_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                continue

            if last_completed_date is None:
                current_streak = 1
                last_completed_date = curr_date
            else:
                diff = (curr_date - last_completed_date).days
                if diff == 1:
                    current_streak += 1
                    last_completed_date = curr_date
                elif diff == 0:
                    continue
                else:
                    missed = diff - 1
                    if missed <= available_freezes:
                        available_freezes -= missed
                        current_streak += 1
                        last_completed_date = curr_date
                    else:
                        current_streak = 1
                        last_completed_date = curr_date
                        last_rewarded_streak = 0

            if current_streak > longest_streak:
                longest_streak = current_streak

            # Check and grant reward milestone
            if active_rule:
                req = active_rule.required_consecutive_days
                if current_streak - last_rewarded_streak >= req:
                    granted = active_rule.freezes_to_grant
                    available_freezes = min(
                        available_freezes + granted, active_rule.max_freezes_allowed
                    )
                    last_rewarded_streak = current_streak

                    # Save to reward history
                    await StreakRepository.create_reward_history(
                        user_id=user_id,
                        rule_id=active_rule.id,
                        freezes_granted=granted,
                        streak_at_reward=current_streak,
                    )

        # Update and save the UserStreak document
        user_streak.current_streak = current_streak
        user_streak.longest_streak = longest_streak
        user_streak.available_freezes = available_freezes
        user_streak.last_rewarded_streak = last_rewarded_streak
        user_streak.last_completed_date = (
            last_completed_date.strftime("%Y-%m-%d") if last_completed_date else None
        )
        user_streak.updated_at = datetime.utcnow()

        await user_streak.save()
        return user_streak

    async def update_streak_on_task_status_change(
        self, user_id: PydanticObjectId, task_date: str, is_completed: bool
    ) -> None:
        # Check if the user has other completed tasks on this date
        completed_tasks_on_date = await Task.find(
            Task.user_id == user_id,
            Task.date == task_date,
            Task.status == TaskStatus.COMPLETED,
        ).to_list()

        # If it was completed, and now we are marking it as completed again or there are other completed tasks:
        # Or if it was marked as not completed, but there are still other completed tasks on the same day:
        # In both cases, the day's completion status remains unchanged.
        # We only need to trigger recalculation if the completed-day status of this date changes.
        # So we recalculate to keep things simple and perfectly correct.
        await self.recalculate_user_streak(user_id)

    async def get_streak_history(
        self, user_id: PydanticObjectId, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None
    ) -> List[dict]:
        # 1. Fetch unique sorted completed task dates
        completed_tasks = await Task.find(
            Task.user_id == user_id, Task.status == TaskStatus.COMPLETED
        ).to_list()
        completed_dates = sorted(list(set(t.date for t in completed_tasks)))

        # 2. Get active rule configurations
        active_rule = await self.get_active_streak_rule()

        # 3. Determine start and end date
        today = date.today()
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except Exception:
                end_date = today
        else:
            end_date = today

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except Exception:
                start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=90)

        # 4. Simulate timeline from first completed date (or start_date, whichever is earlier)
        # to ensure freezes and streak counts are correctly calculated leading up to our range.
        sim_start = start_date
        if completed_dates:
            try:
                first_completed = datetime.strptime(completed_dates[0], "%Y-%m-%d").date()
                if first_completed < sim_start:
                    sim_start = first_completed
            except Exception:
                pass

        current_streak = 0
        available_freezes = 0
        last_rewarded_streak = 0
        last_completed_date: Optional[date] = None

        all_day_statuses = {}
        completed_set = set(completed_dates)

        curr = sim_start
        while curr <= end_date:
            date_str = curr.strftime("%Y-%m-%d")

            if date_str in completed_set:
                all_day_statuses[date_str] = "completed"
                if last_completed_date is None:
                    current_streak = 1
                else:
                    diff = (curr - last_completed_date).days
                    if diff == 1:
                        current_streak += 1
                
                last_completed_date = curr

                # Check and grant freezes
                if active_rule:
                    req = active_rule.required_consecutive_days
                    if current_streak - last_rewarded_streak >= req:
                        granted = active_rule.freezes_to_grant
                        available_freezes = min(
                            available_freezes + granted, active_rule.max_freezes_allowed
                        )
                        last_rewarded_streak = current_streak
            else:
                if last_completed_date is not None:
                    if available_freezes > 0:
                        available_freezes -= 1
                        current_streak += 1
                        last_completed_date = curr
                        all_day_statuses[date_str] = "freezed"
                    else:
                        current_streak = 0
                        last_rewarded_streak = 0
                        all_day_statuses[date_str] = "missed"
                else:
                    all_day_statuses[date_str] = "empty"

            curr += timedelta(days=1)

        # 5. Filter and format the results to the requested range [start_date, end_date]
        result = []
        curr = start_date
        while curr <= end_date:
            date_str = curr.strftime("%Y-%m-%d")
            status = all_day_statuses.get(date_str, "empty")
            result.append({
                "date": date_str,
                "status": status
            })
            curr += timedelta(days=1)

        return result
