import contextvars
from typing import Optional

from mcp.server.fastmcp import FastMCP

from app.core.db_config import init_db
from app.models.user import User
from app.services import mcp_tools

# Define a ContextVar to store the active authenticated user during HTTP/SSE requests
mcp_user_var: contextvars.ContextVar[Optional[User]] = contextvars.ContextVar(
    "mcp_user", default=None
)

# Initialize the FastMCP server
mcp = FastMCP("WeeklyPlannerMCP")

db_initialized = False


async def ensure_db():
    """Lazily initialize the MongoDB/Beanie database connection."""
    global db_initialized
    if not db_initialized:
        await init_db()
        db_initialized = True


async def get_mcp_user() -> User:
    """
    Authenticate the caller for MCP tools.
    1. Checks if mcp_user_var ContextVar is set (populated by FastAPI SSE HTTP middleware).
    2. Falls back to reading AUTH_TOKEN (JWT) or MCP_USER_EMAIL from the environment (for stdio transport).
    """
    await ensure_db()

    # 1. Check ContextVar (HTTP SSE flow)
    user = mcp_user_var.get()
    if user:
        return user

    # 2. Check environment variables (stdio transport flow)
    import os

    import jwt

    from app.core.settings import setting
    from app.repositories import UserRepository

    # Check JWT Token first
    token = os.environ.get("AUTH_TOKEN")
    if token:
        try:
            payload = jwt.decode(
                token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM]
            )
            user_id = payload.get("user_id")
            if user_id:
                user = await UserRepository.get_user_by_id(user_id)
                if user:
                    return user
        except Exception as e:
            raise ValueError(f"Failed to authenticate AUTH_TOKEN: {str(e)}")

    # Check developer email fallback
    email = os.environ.get("MCP_USER_EMAIL")
    if email:
        user = await UserRepository.get_user_by_email(email)
        if user:
            return user
        raise ValueError(f"User with email '{email}' not found")

    raise ValueError(
        "Authentication required. Set AUTH_TOKEN or MCP_USER_EMAIL for stdio, or supply a token for SSE."
    )


# --- User Tools ---


@mcp.tool()
async def create_task(
    title: str,
    date: str,
    startTime: str,
    endTime: str,
    priority: str = "medium",
    description: Optional[str] = None,
) -> str:
    """
    Create a new task for the authenticated user.
    - title: Title of the task
    - date: Date in YYYY-MM-DD format
    - startTime: Start time in HH:mm format
    - endTime: End time in HH:mm format
    - priority: Priority, one of 'high', 'medium', 'low'
    - description: Optional description of the task
    """
    user = await get_mcp_user()
    return await mcp_tools.create_task_tool(
        user=user,
        title=title,
        date=date,
        startTime=startTime,
        endTime=endTime,
        priority=priority,
        description=description,
    )


@mcp.tool()
async def list_my_tasks(
    from_date: Optional[str] = None, end_date: Optional[str] = None
) -> str:
    """
    List tasks belonging to the authenticated user.
    - from_date: Optional filter in YYYY-MM-DD format
    - end_date: Optional filter in YYYY-MM-DD format
    """
    user = await get_mcp_user()
    return await mcp_tools.list_my_tasks_tool(
        user=user, from_date=from_date, end_date=end_date
    )


@mcp.tool()
async def get_task_by_title(title: str) -> str:
    """
    Search for tasks matching a given title/name for the authenticated user.
    - title: Title of the task to search for
    """
    user = await get_mcp_user()
    return await mcp_tools.get_task_by_title_tool(user=user, title=title)


@mcp.tool()
async def update_task(
    task_id: str,
    title: Optional[str] = None,
    date: Optional[str] = None,
    startTime: Optional[str] = None,
    endTime: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    Update details of a task belonging to the authenticated user.
    - task_id: The ID of the task to update
    - title: Optional new title
    - date: Optional new date in YYYY-MM-DD format
    - startTime: Optional new start time in HH:mm format
    - endTime: Optional new end time in HH:mm format
    - priority: Optional new priority (high, medium, low)
    - status: Optional new status (pending, completed, skipped)
    - description: Optional new description
    """
    user = await get_mcp_user()
    return await mcp_tools.update_task_tool(
        user=user,
        task_id=task_id,
        title=title,
        date=date,
        startTime=startTime,
        endTime=endTime,
        priority=priority,
        status=status,
        description=description,
    )


@mcp.tool()
async def delete_task(task_id: str) -> str:
    """
    Delete a task belonging to the authenticated user.
    - task_id: The ID of the task to delete
    """
    user = await get_mcp_user()
    return await mcp_tools.delete_task_tool(user=user, task_id=task_id)


# --- Admin Tools ---


@mcp.tool()
async def admin_list_all_tasks() -> str:
    """
    [ADMIN ONLY] List all tasks of all users in the system.
    """
    user = await get_mcp_user()
    return await mcp_tools.admin_list_all_tasks_tool(user=user)


@mcp.tool()
async def admin_get_users_by_name(name: str) -> str:
    """
    [ADMIN ONLY] Search for users in the system by name or email.
    - name: Query string (name or email fragment)
    """
    user = await get_mcp_user()
    return await mcp_tools.admin_get_users_by_name_tool(user=user, name=name)


if __name__ == "__main__":
    # Runs the server over stdio by default
    mcp.run(transport="stdio")
