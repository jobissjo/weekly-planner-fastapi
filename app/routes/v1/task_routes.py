from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.core.permissions import any_user_role
from app.models.user import User
from app.schemas.common_schema import BaseResponse
from app.schemas.task_schema import (
    TaskCreateSchema,
    TaskUpdateSchema,
    TaskResponse,
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
