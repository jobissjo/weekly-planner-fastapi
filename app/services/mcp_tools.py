from typing import List, Optional
import uuid
from datetime import date

from app.models.enums import TaskPriority, TaskStatus, UserRole
from app.models.task import Task, Subtask
from app.models.user import User
from app.models.streak import UserStreak
from app.repositories import UserRepository
from app.services.task_service import TaskService
from app.services.streak_service import StreakService

task_service = TaskService()
streak_service = StreakService()


async def create_task_tool(
    user: User,
    title: str,
    date: str,
    startTime: str,
    endTime: str,
    priority: str = "medium",
    description: Optional[str] = None,
    specializedTitle: Optional[str] = None,
    recurrence: str = "none",
    recurrenceEndDate: Optional[str] = None,
    weeklyDays: Optional[List[int]] = None,
    monthlyDay: Optional[int] = None,
) -> str:
    """
    Create a new task for the authenticated user.
    """
    try:
        from app.schemas.task_schema import TaskCreateSchema

        # Check for duplicate tasks with same title, date, and startTime
        existing_tasks = await task_service.get_tasks_by_title(title, user.id)
        for t in existing_tasks:
            if (
                t.title.lower() == title.lower()
                and t.date == date
                and t.startTime == startTime
            ):
                return f"Notice: A task named '{title}' already exists on {date} at {startTime} (ID: {t.id}, Status: {t.status.value}). Creation skipped to avoid duplicates."

        # Parse priority
        try:
            task_priority = TaskPriority(priority.lower())
        except ValueError:
            task_priority = TaskPriority.MEDIUM

        try:
            from app.models.enums import RecurrencePattern

            rec_pattern = RecurrencePattern(recurrence.lower())
        except ValueError:
            from app.models.enums import RecurrencePattern

            rec_pattern = RecurrencePattern.NONE

        schema = TaskCreateSchema(
            title=title,
            specializedTitle=specializedTitle,
            date=date,
            startTime=startTime,
            endTime=endTime,
            priority=task_priority,
            description=description,
            recurrence=rec_pattern,
            recurrenceEndDate=recurrenceEndDate,
            weeklyDays=weeklyDays,
            monthlyDay=monthlyDay,
        )
        task = await task_service.create_task(user.id, schema)
        spec_text = f" (Focus: {specializedTitle})" if specializedTitle else ""
        rec_text = (
            f" [Recurrence: {rec_pattern.value}]"
            if rec_pattern != RecurrencePattern.NONE
            else ""
        )
        return f"Success: Task '{task.title}'{spec_text} created with ID: {task.id} on {task.date} ({task.startTime}-{task.endTime}){rec_text}."
    except Exception as e:
        return f"Error creating task: {str(e)}"


async def list_my_tasks_tool(
    user: User, from_date: Optional[str] = None, end_date: Optional[str] = None
) -> str:
    """
    List tasks of the authenticated user.
    """
    try:
        tasks = await task_service.list_tasks(user.id, from_date, end_date)
        if not tasks:
            return "No tasks found."

        lines = []
        for t in tasks:
            lines.append(
                f"- [{t.status.value}] {t.title} on {t.date} from {t.startTime} to {t.endTime} (Priority: {t.priority.value}, ID: {t.id})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing tasks: {str(e)}"


async def get_task_by_title_tool(user: User, title: str) -> str:
    """
    Get tasks by their title/name for the authenticated user.
    """
    try:
        tasks = await task_service.get_tasks_by_title(title, user.id)
        if not tasks:
            return f"No tasks found matching title: '{title}'."

        lines = []
        for t in tasks:
            lines.append(
                f"- [{t.status.value}] {t.title} on {t.date} from {t.startTime} to {t.endTime} (Priority: {t.priority.value}, ID: {t.id})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching tasks: {str(e)}"


async def update_task_tool(
    user: User,
    task_id: str,
    title: Optional[str] = None,
    specializedTitle: Optional[str] = None,
    date: Optional[str] = None,
    startTime: Optional[str] = None,
    endTime: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    completedDate: Optional[str] = None,
    completionNotes: Optional[str] = None,
) -> str:
    """
    Update a task belonging to the authenticated user.
    """
    try:
        from app.schemas.task_schema import TaskUpdateSchema

        update_data = {}
        if title is not None:
            update_data["title"] = title
        if specializedTitle is not None:
            update_data["specializedTitle"] = specializedTitle
        if date is not None:
            update_data["date"] = date
        if startTime is not None:
            update_data["startTime"] = startTime
        if endTime is not None:
            update_data["endTime"] = endTime
        if description is not None:
            update_data["description"] = description
        if completedDate is not None:
            update_data["completedDate"] = completedDate
        if completionNotes is not None:
            update_data["completionNotes"] = completionNotes
        if priority is not None:
            try:
                update_data["priority"] = TaskPriority(priority.lower())
            except ValueError:
                pass
        if status is not None:
            try:
                update_data["status"] = TaskStatus(status.lower())
            except ValueError:
                pass

        schema = TaskUpdateSchema(**update_data)
        updated_task = await task_service.update_task(task_id, user.id, schema)
        return f"Success: Task '{updated_task.title}' updated successfully. New status: {updated_task.status.value}."
    except Exception as e:
        return f"Error updating task: {str(e)}"


async def mark_task_completed_tool(
    user: User,
    task_id: str,
    completedDate: Optional[str] = None,
    completionNotes: Optional[str] = None,
) -> str:
    """
    Mark a task belonging to the authenticated user as completed.
    """
    try:
        from app.schemas.task_schema import TaskUpdateSchema

        update_data = {"status": TaskStatus.COMPLETED}
        if completedDate is not None:
            update_data["completedDate"] = completedDate
        if completionNotes is not None:
            update_data["completionNotes"] = completionNotes

        schema = TaskUpdateSchema(**update_data)
        updated_task = await task_service.update_task(task_id, user.id, schema)
        return f"Success: Task '{updated_task.title}' marked as completed. Completed Date: {updated_task.completedDate}. Notes: {updated_task.completionNotes}."
    except Exception as e:
        return f"Error marking task as completed: {str(e)}"


async def delete_task_tool(user: User, task_id: str) -> str:
    """
    Delete a task belonging to the authenticated user.
    """
    try:
        await task_service.delete_task(task_id, user.id)
        return f"Success: Task with ID {task_id} deleted."
    except Exception as e:
        return f"Error deleting task: {str(e)}"


async def admin_list_all_tasks_tool(user: User) -> str:
    """
    [ADMIN ONLY] List all tasks of all users in the system.
    """
    if user.role != UserRole.ADMIN and not user.is_superuser:
        return "Error: Permission denied. Admin role required."

    try:
        tasks = await Task.find_all().to_list()
        if not tasks:
            return "No tasks exist in the database."

        lines = []
        for t in tasks:
            lines.append(
                f"- User: {t.user_id} | [{t.status.value}] {t.title} on {t.date} (ID: {t.id})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing all tasks: {str(e)}"


async def admin_get_users_by_name_tool(user: User, name: str) -> str:
    """
    [ADMIN ONLY] Search for users by name or email.
    """
    if user.role != UserRole.ADMIN and not user.is_superuser:
        return "Error: Permission denied. Admin role required."

    try:
        users = await UserRepository.get_users_by_name(name)
        if not users:
            return f"No users found matching query: '{name}'."

        lines = []
        for u in users:
            lines.append(
                f"- {u.first_name} {u.last_name} ({u.email}, Role: {u.role.value}, Active: {u.is_active}, ID: {u.id})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching users: {str(e)}"


async def get_user_streak_tool(user: User, today_str: Optional[str] = None) -> str:
    """
    Get the streak status for the authenticated user.
    """
    try:
        today_date = today_str or date.today().isoformat()
        streak = await streak_service.get_user_streak(user.id, today_date)
        return (
            f"User Streak Status:\n"
            f"- Current Streak: {streak.current_streak} days\n"
            f"- Longest Streak: {streak.longest_streak} days\n"
            f"- Available Freezes: {streak.available_freezes}\n"
            f"- Is Streak Active Today: {streak.is_streak_active}\n"
            f"- Last Active Date: {streak.last_active_date}"
        )
    except Exception as e:
        return f"Error fetching streak: {str(e)}"


async def freeze_streak_tool(user: User, today_str: Optional[str] = None) -> str:
    """
    Use an available freeze to protect the user's streak for today.
    """
    try:
        today_date = today_str or date.today().isoformat()
        streak = await streak_service.use_freeze(user.id, today_date)
        return f"Success: Streak freeze applied! Current streak remains at {streak.current_streak} days. Freezes left: {streak.available_freezes}."
    except Exception as e:
        return f"Error freezing streak: {str(e)}"


async def get_user_gamification_profile_tool(user: User) -> str:
    """
    Get gamification profile details (XP, Level, Theme, Avatar Border) for the user.
    """
    try:
        profile = await UserRepository.get_user_profile_by_id(str(user.id))
        xp = getattr(profile, "xp", 350) if profile else 350
        level = getattr(profile, "level", 1) if profile else 1
        active_theme = getattr(profile, "active_theme", "system") if profile else "system"
        unlocked_themes = getattr(profile, "unlocked_themes", ["light", "dark", "system"]) if profile else ["light", "dark", "system"]
        active_border = getattr(profile, "active_border", "default") if profile else "default"

        return (
            f"User Gamification Profile:\n"
            f"- XP: {xp} points\n"
            f"- Level: {level}\n"
            f"- Active Theme: {active_theme}\n"
            f"- Unlocked Themes: {', '.join(unlocked_themes)}\n"
            f"- Active Avatar Border: {active_border}"
        )
    except Exception as e:
        return f"Error fetching gamification profile: {str(e)}"


async def update_user_theme_tool(user: User, theme: str) -> str:
    """
    Update the active app theme for the user.
    """
    try:
        theme_clean = theme.lower().strip()
        allowed = ["light", "dark", "system", "cyberpunk", "forest", "sunset"]
        if theme_clean not in allowed:
            return f"Error: Theme '{theme}' is invalid. Allowed options: {', '.join(allowed)}."

        profile = await UserRepository.get_user_profile_by_id(str(user.id))
        if not profile:
            profile = await UserRepository.update_notification_preferences(str(user.id), True, True)

        profile.active_theme = theme_clean
        if hasattr(profile, "unlocked_themes") and theme_clean not in profile.unlocked_themes:
            profile.unlocked_themes.append(theme_clean)

        await profile.save()
        return f"Success: App theme updated to '{theme_clean}'."
    except Exception as e:
        return f"Error updating theme: {str(e)}"


async def add_subtasks_tool(user: User, task_id: str, subtask_titles: List[str]) -> str:
    """
    Add subtask checklist items to a task belonging to the user.
    """
    try:
        task = await Task.get(task_id)
        if not task or str(task.user_id) != str(user.id):
            return f"Error: Task with ID '{task_id}' not found."

        if task.subtasks is None:
            task.subtasks = []

        added = []
        for st_title in subtask_titles:
            new_st = Subtask(id=str(uuid.uuid4())[:8], title=st_title, completed=False)
            task.subtasks.append(new_st)
            added.append(st_title)

        await task.save()
        return f"Success: Added {len(added)} subtask(s) to '{task.title}': {', '.join(added)}."
    except Exception as e:
        return f"Error adding subtasks: {str(e)}"


async def toggle_subtask_tool(user: User, task_id: str, subtask_id: str) -> str:
    """
    Toggle a subtask item between completed and pending.
    """
    try:
        task = await Task.get(task_id)
        if not task or str(task.user_id) != str(user.id):
            return f"Error: Task with ID '{task_id}' not found."

        if not task.subtasks:
            return f"Error: Task '{task.title}' has no subtasks."

        found = False
        new_state = False
        st_title = ""
        for st in task.subtasks:
            if st.id == subtask_id or st.title.lower() == subtask_id.lower():
                st.completed = not st.completed
                new_state = st.completed
                st_title = st.title
                found = True
                break

        if not found:
            return f"Error: Subtask '{subtask_id}' not found under task '{task.title}'."

        await task.save()
        status_label = "completed" if new_state else "pending"
        return f"Success: Subtask '{st_title}' under '{task.title}' marked as {status_label}."
    except Exception as e:
        return f"Error toggling subtask: {str(e)}"


async def generate_daily_briefing_tool(user: User, date_str: Optional[str] = None) -> str:
    """
    Generate a daily briefing summary for the user.
    """
    try:
        target_date = date_str or date.today().isoformat()
        tasks = await task_service.list_tasks(user.id, from_date=target_date, end_date=target_date)
        streak = await streak_service.get_user_streak(user.id, target_date)

        pending_count = len([t for t in tasks if t.status == TaskStatus.PENDING])
        completed_count = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        high_prio = [t.title for t in tasks if t.priority == TaskPriority.HIGH and t.status == TaskStatus.PENDING]

        briefing = [
            f"🌅 Daily Briefing for {user.first_name} ({target_date}):",
            f"- Current Streak: {streak.current_streak} days 🔥",
            f"- Total Tasks Scheduled Today: {len(tasks)} ({pending_count} pending, {completed_count} completed)",
        ]

        if high_prio:
            briefing.append(f"- High Priority Focus Areas: {', '.join(high_prio)}")
        else:
            briefing.append("- No high priority urgent tasks scheduled. Great pace!")

        return "\n".join(briefing)
    except Exception as e:
        return f"Error generating daily briefing: {str(e)}"

