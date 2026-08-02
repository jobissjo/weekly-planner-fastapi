from datetime import datetime
from typing import List, Optional
from beanie import PydanticObjectId
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.permissions import any_user_role, only_admin
from app.core.security import hash_password, verify_password
from app.models.habit_quitter import (
    BadHabit,
    HabitAttempt,
    HabitJournalLog,
    HabitVaultPin,
    SystemConfig,
)
from app.models.profile import Profile
from app.models.user import User
from app.schemas.common_schema import BaseResponse
from app.schemas.habit_schema import (
    AdminHabitLimitSchema,
    BadHabitCreateSchema,
    JournalLogSchema,
    PinResetSchema,
    PinSetSchema,
    PinVerifySchema,
    RelapseSchema,
)
from app.utils.common import CustomException

router = APIRouter(prefix="/habits", tags=["Habit Quitter"])

DEFAULT_HABIT_LIMIT = 3


async def get_max_habit_limit() -> int:
    config = await SystemConfig.find_one(SystemConfig.key == "max_bad_habits_limit")
    if config and config.value.isdigit():
        return int(config.value)
    return DEFAULT_HABIT_LIMIT


def calculate_days_clean(start_date_str: str) -> int:
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        today_dt = datetime.utcnow().date()
        diff = (today_dt - start_dt).days
        return max(0, diff)
    except Exception:
        return 0


# --- PIN & Security Routes ---


@router.get("/pin/status", response_model=BaseResponse[dict])
async def check_pin_status(current_user: User = Depends(any_user_role)):
    pin_doc = await HabitVaultPin.find_one(HabitVaultPin.user_id == current_user.id)
    return BaseResponse(
        status="success",
        message="PIN status fetched",
        data={"has_pin": pin_doc is not None},
    )


@router.post("/pin/set", response_model=BaseResponse[dict])
async def set_pin(data: PinSetSchema, current_user: User = Depends(any_user_role)):
    hashed = await hash_password(data.pin)
    pin_doc = await HabitVaultPin.find_one(HabitVaultPin.user_id == current_user.id)
    if pin_doc:
        pin_doc.pin_hash = hashed
        pin_doc.updated_at = datetime.utcnow()
        await pin_doc.save()
    else:
        pin_doc = HabitVaultPin(user_id=current_user.id, pin_hash=hashed)
        await pin_doc.insert()

    return BaseResponse(
        status="success",
        message="4-digit vault PIN set successfully",
        data={"has_pin": True},
    )


@router.post("/pin/verify", response_model=BaseResponse[dict])
async def verify_pin(data: PinVerifySchema, current_user: User = Depends(any_user_role)):
    pin_doc = await HabitVaultPin.find_one(HabitVaultPin.user_id == current_user.id)
    if not pin_doc:
        raise CustomException("No PIN set yet", 400)

    is_valid = await verify_password(data.pin, pin_doc.pin_hash)
    if not is_valid:
        raise CustomException("Incorrect 4-digit PIN", 400)

    return BaseResponse(
        status="success",
        message="PIN verified successfully",
        data={"verified": True},
    )


@router.post("/pin/reset-with-password", response_model=BaseResponse[dict])
async def reset_pin_with_password(
    data: PinResetSchema, current_user: User = Depends(any_user_role)
):
    if not current_user.password:
        raise CustomException("No password configured on this account", 400)

    is_valid = await verify_password(data.account_password, current_user.password)
    if not is_valid:
        raise CustomException("Incorrect account password", 400)

    hashed_new_pin = await hash_password(data.new_pin)
    pin_doc = await HabitVaultPin.find_one(HabitVaultPin.user_id == current_user.id)
    if pin_doc:
        pin_doc.pin_hash = hashed_new_pin
        pin_doc.updated_at = datetime.utcnow()
        await pin_doc.save()
    else:
        pin_doc = HabitVaultPin(user_id=current_user.id, pin_hash=hashed_new_pin)
        await pin_doc.insert()

    return BaseResponse(
        status="success",
        message="PIN reset successfully using main password",
        data={"has_pin": True},
    )


# --- Bad Habit Management Routes ---


@router.get("", response_model=BaseResponse[dict])
async def list_habits(current_user: User = Depends(any_user_role)):
    habits = await BadHabit.find(
        BadHabit.user_id == current_user.id, BadHabit.is_active == True
    ).to_list()
    max_limit = await get_max_habit_limit()

    formatted = []
    for h in habits:
        days_clean = calculate_days_clean(h.start_date)
        formatted.append(
            {
                "id": str(h.id),
                "title": h.title,
                "description": h.description,
                "target_days": h.target_days,
                "start_date": h.start_date,
                "current_attempt_number": h.current_attempt_number,
                "days_clean": days_clean,
                "progress_pct": min(100, round((days_clean / max(1, h.target_days)) * 100)),
                "attempts": [a.model_dump() for a in h.attempts],
            }
        )

    return BaseResponse(
        status="success",
        message="Habits fetched successfully",
        data={
            "habits": formatted,
            "max_limit": max_limit,
            "can_add": len(habits) < max_limit,
        },
    )


@router.post("", response_model=BaseResponse[dict])
async def create_habit(
    data: BadHabitCreateSchema, current_user: User = Depends(any_user_role)
):
    active_habits = await BadHabit.find(
        BadHabit.user_id == current_user.id, BadHabit.is_active == True
    ).to_list()
    max_limit = await get_max_habit_limit()

    if len(active_habits) >= max_limit:
        raise CustomException(
            f"You have reached the maximum allowed limit of {max_limit} active habits.", 400
        )

    habit = BadHabit(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        target_days=data.target_days,
        start_date=data.start_date,
    )
    await habit.insert()

    return BaseResponse(
        status="success",
        message="Bad habit tracker created successfully",
        data={"id": str(habit.id), "title": habit.title},
    )


@router.delete("/{id}", response_model=BaseResponse[None])
async def delete_habit(id: str, current_user: User = Depends(any_user_role)):
    habit = await BadHabit.find_one(
        BadHabit.id == PydanticObjectId(id), BadHabit.user_id == current_user.id
    )
    if not habit:
        raise CustomException("Habit not found", 404)

    habit.is_active = False
    await habit.save()

    return BaseResponse(status="success", message="Habit deleted successfully", data=None)


@router.post("/{id}/relapse", response_model=BaseResponse[dict])
async def mark_relapse(
    id: str, data: RelapseSchema, current_user: User = Depends(any_user_role)
):
    habit = await BadHabit.find_one(
        BadHabit.id == PydanticObjectId(id), BadHabit.user_id == current_user.id
    )
    if not habit:
        raise CustomException("Habit not found", 404)

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    days_clean = calculate_days_clean(habit.start_date)

    # Save failed attempt
    attempt = HabitAttempt(
        attempt_number=habit.current_attempt_number,
        start_date=habit.start_date,
        end_date=today_str,
        days_achieved=days_clean,
        relapse_reason=data.relapse_reason,
    )
    habit.attempts.append(attempt)

    # Reset for next attempt from Day 1
    habit.current_attempt_number += 1
    habit.start_date = today_str
    habit.updated_at = datetime.utcnow()
    await habit.save()

    return BaseResponse(
        status="success",
        message="Relapse logged. Restarted from Day 1. Every step forward counts!",
        data={
            "days_achieved": days_clean,
            "new_attempt_number": habit.current_attempt_number,
            "new_start_date": today_str,
        },
    )


@router.post("/{id}/journal", response_model=BaseResponse[dict])
async def add_journal_log(
    id: str, data: JournalLogSchema, current_user: User = Depends(any_user_role)
):
    habit = await BadHabit.find_one(
        BadHabit.id == PydanticObjectId(id), BadHabit.user_id == current_user.id
    )
    if not habit:
        raise CustomException("Habit not found", 404)

    # Check existing log for today
    existing_log = await HabitJournalLog.find_one(
        HabitJournalLog.habit_id == habit.id, HabitJournalLog.date == data.date
    )
    if existing_log:
        existing_log.struggle_level = data.struggle_level
        existing_log.notes = data.notes
        existing_log.triggers = data.triggers
        await existing_log.save()
        log = existing_log
    else:
        log = HabitJournalLog(
            habit_id=habit.id,
            user_id=current_user.id,
            date=data.date,
            struggle_level=data.struggle_level,
            notes=data.notes,
            triggers=data.triggers,
        )
        await log.insert()

    # Award bonus XP for daily check-in (+50 XP)
    xp_earned = 50
    profile = await Profile.find_one(Profile.user.id == current_user.id)
    if profile:
        profile.xp += xp_earned
        profile.level = (profile.xp // 500) + 1
        await profile.save()

    return BaseResponse(
        status="success",
        message=f"Journal log saved! +{xp_earned} XP earned.",
        data={"log_id": str(log.id), "xp_earned": xp_earned},
    )


@router.get("/{id}/journal", response_model=BaseResponse[List[dict]])
async def list_journal_logs(id: str, current_user: User = Depends(any_user_role)):
    habit = await BadHabit.find_one(
        BadHabit.id == PydanticObjectId(id), BadHabit.user_id == current_user.id
    )
    if not habit:
        raise CustomException("Habit not found", 404)

    logs = await HabitJournalLog.find(
        HabitJournalLog.habit_id == habit.id
    ).sort(-HabitJournalLog.created_at).to_list()

    formatted = [
        {
            "id": str(l.id),
            "date": l.date,
            "struggle_level": l.struggle_level,
            "notes": l.notes,
            "triggers": l.triggers,
        }
        for l in logs
    ]

    return BaseResponse(
        status="success",
        message="Journal logs retrieved",
        data=formatted,
    )


# --- Admin Routes ---


@router.get("/admin/limit", response_model=BaseResponse[dict])
async def admin_get_limit(admin_user: User = Depends(only_admin)):
    limit = await get_max_habit_limit()
    return BaseResponse(
        status="success",
        message="Admin habit limit retrieved",
        data={"max_bad_habits_limit": limit},
    )


@router.patch("/admin/limit", response_model=BaseResponse[dict])
async def admin_update_limit(
    data: AdminHabitLimitSchema, admin_user: User = Depends(only_admin)
):
    config = await SystemConfig.find_one(SystemConfig.key == "max_bad_habits_limit")
    if config:
        config.value = str(data.max_bad_habits_limit)
        await config.save()
    else:
        config = SystemConfig(key="max_bad_habits_limit", value=str(data.max_bad_habits_limit))
        await config.insert()

    return BaseResponse(
        status="success",
        message="Max bad habits limit updated by admin",
        data={"max_bad_habits_limit": data.max_bad_habits_limit},
    )
