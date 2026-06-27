from typing import List, Optional
from beanie import PydanticObjectId
from app.models.user import User
from app.models.task import Task
from app.models.enums import UserRole, TaskPriority, TaskStatus
from app.services.task_service import TaskService
from app.repositories import UserRepository
from app.utils.common import CustomException

task_service = TaskService()

async def create_task_tool(
    user: User,
    title: str,
    date: str,
    startTime: str,
    endTime: str,
    priority: str = "medium",
    description: Optional[str] = None
) -> str:
    """
    Create a new task for the authenticated user.
    """
    try:
        from app.schemas.task_schema import TaskCreateSchema
        
        # Parse priority
        try:
            task_priority = TaskPriority(priority.lower())
        except ValueError:
            task_priority = TaskPriority.MEDIUM

        schema = TaskCreateSchema(
            title=title,
            date=date,
            startTime=startTime,
            endTime=endTime,
            priority=task_priority,
            description=description
        )
        task = await task_service.create_task(user.id, schema)
        return f"Success: Task '{task.title}' created with ID: {task.id} on {task.date} ({task.startTime}-{task.endTime})."
    except Exception as e:
        return f"Error creating task: {str(e)}"

async def list_my_tasks_tool(
    user: User,
    from_date: Optional[str] = None,
    end_date: Optional[str] = None
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
            lines.append(f"- [{t.status.value}] {t.title} on {t.date} from {t.startTime} to {t.endTime} (Priority: {t.priority.value}, ID: {t.id})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing tasks: {str(e)}"

async def get_task_by_title_tool(
    user: User,
    title: str
) -> str:
    """
    Get tasks by their title/name for the authenticated user.
    """
    try:
        tasks = await task_service.get_tasks_by_title(title, user.id)
        if not tasks:
            return f"No tasks found matching title: '{title}'."
        
        lines = []
        for t in tasks:
            lines.append(f"- [{t.status.value}] {t.title} on {t.date} from {t.startTime} to {t.endTime} (Priority: {t.priority.value}, ID: {t.id})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching tasks: {str(e)}"

async def update_task_tool(
    user: User,
    task_id: str,
    title: Optional[str] = None,
    date: Optional[str] = None,
    startTime: Optional[str] = None,
    endTime: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Update a task belonging to the authenticated user.
    """
    try:
        from app.schemas.task_schema import TaskUpdateSchema
        
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if date is not None:
            update_data["date"] = date
        if startTime is not None:
            update_data["startTime"] = startTime
        if endTime is not None:
            update_data["endTime"] = endTime
        if description is not None:
            update_data["description"] = description
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

async def delete_task_tool(
    user: User,
    task_id: str
) -> str:
    """
    Delete a task belonging to the authenticated user.
    """
    try:
        await task_service.delete_task(task_id, user.id)
        return f"Success: Task with ID {task_id} deleted."
    except Exception as e:
        return f"Error deleting task: {str(e)}"

async def admin_list_all_tasks_tool(
    user: User
) -> str:
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
            lines.append(f"- User: {t.user_id} | [{t.status.value}] {t.title} on {t.date} (ID: {t.id})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing all tasks: {str(e)}"

async def admin_get_users_by_name_tool(
    user: User,
    name: str
) -> str:
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
            lines.append(f"- {u.first_name} {u.last_name} ({u.email}, Role: {u.role.value}, Active: {u.is_active}, ID: {u.id})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching users: {str(e)}"
