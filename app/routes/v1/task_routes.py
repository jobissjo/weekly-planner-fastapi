from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.core.permissions import any_user_role, only_admin
from app.models.task import Task
from app.models.user import User
from app.schemas.common_schema import BaseResponse
from app.schemas.task_schema import (
    TaskCreateSchema,
    TaskResponse,
    TaskUpdateSchema,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])
task_service = TaskService()


@router.post("", response_model=BaseResponse[TaskResponse])
async def create_task(
    data: TaskCreateSchema,
    current_user: User = Depends(any_user_role),
):
    task = await task_service.create_task(current_user.id, data)
    return BaseResponse(
        status="success",
        message="Task created successfully",
        data=TaskResponse.model_validate(task),
    )


@router.get("", response_model=BaseResponse[List[TaskResponse]])
async def list_tasks(
    from_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: User = Depends(any_user_role),
):

    tasks = await task_service.list_tasks(current_user.id, from_date, end_date)
    data = [TaskResponse.model_validate(t) for t in tasks]
    return BaseResponse(
        status="success",
        message="Tasks retrieved successfully",
        data=data,
    )


@router.get("/{id}", response_model=BaseResponse[TaskResponse])
async def get_task(
    id: str,
    current_user: User = Depends(any_user_role),
):
    task = await task_service.get_task_by_id(id, current_user.id)
    return BaseResponse(
        status="success",
        message="Task retrieved successfully",
        data=TaskResponse.model_validate(task),
    )


@router.patch("/{id}", response_model=BaseResponse[TaskResponse])
async def update_task(
    id: str,
    data: TaskUpdateSchema,
    current_user: User = Depends(any_user_role),
):
    task = await task_service.update_task(id, current_user.id, data)
    return BaseResponse(
        status="success",
        message="Task updated successfully",
        data=TaskResponse.model_validate(task),
    )


@router.delete("/{id}", response_model=BaseResponse[None])
async def delete_task(
    id: str,
    current_user: User = Depends(any_user_role),
):
    await task_service.delete_task(id, current_user.id)
    return BaseResponse(
        status="success",
        message="Task deleted successfully",
        data=None,
    )


@router.get("/admin/all", response_model=BaseResponse[List[TaskResponse]])
async def admin_list_all_tasks(
    admin_user: User = Depends(only_admin),
):
    tasks = await Task.find_all().to_list()
    return BaseResponse(
        status="success",
        message="All tasks retrieved successfully",
        data=[TaskResponse.model_validate(t) for t in tasks],
    )


@router.get("/events")
async def tasks_events(token: str = Query(...)):
    """
    Exposes an SSE stream for tasks events.
    Requires token as a query parameter because EventSource in browsers
    cannot easily customize headers.
    """
    import asyncio
    import json

    import jwt
    from fastapi.responses import StreamingResponse

    from app.core.events import event_manager
    from app.core.settings import setting
    from app.repositories import UserRepository
    from app.utils.common import CustomException

    try:
        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])
        if payload.get("token_type") != "access":
            raise CustomException("Invalid token type", status_code=401)
        user_id = payload.get("user_id")
        if not user_id:
            raise CustomException("Token is missing user id", status_code=401)
        user = await UserRepository.get_user_by_id(user_id)
        if not user:
            raise CustomException("User not found", status_code=401)
    except Exception as e:
        raise CustomException(f"Authentication failed: {str(e)}", status_code=401)

    async def event_generator():
        user_id_str = str(user.id)
        queue = event_manager.subscribe(user_id_str)
        try:
            # Yield connection verification ping
            yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"

            while True:
                # Keep connection alive with a periodic ping if there are no events
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield event
                    queue.task_done()
                except asyncio.TimeoutError:
                    yield f"event: ping\ndata: {json.dumps({'status': 'ping'})}\n\n"
        except asyncio.CancelledError:
            # Unsubscribe user when client disconnects
            event_manager.unsubscribe(user_id_str, queue)
            raise
        except Exception:
            event_manager.unsubscribe(user_id_str, queue)
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering for Nginx/reverse proxies
        },
    )
