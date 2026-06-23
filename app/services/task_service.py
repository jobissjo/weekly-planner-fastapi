from typing import List, Optional
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task_schema import TaskCreateSchema, TaskUpdateSchema
from app.utils.common import CustomException
from beanie import PydanticObjectId
from app.core.logger_config import logger as default_logger


class TaskService:

    def __init__(self, logger=None):
        self.logger = logger or default_logger

    async def create_task(
        self, user_id: PydanticObjectId, schema: TaskCreateSchema
    ) -> Task:
        return await TaskRepository.create_task(user_id, schema)

    async def get_task_by_id(self, task_id: str, user_id: PydanticObjectId) -> Task:
        task = await TaskRepository.get_task_by_id(task_id, user_id)
        if not task:
            raise CustomException("Task not found", status_code=404)
        return task

    async def list_tasks(
        self,
        user_id: PydanticObjectId,
        from_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Task]:
        return await TaskRepository.list_tasks(user_id, from_date, end_date)

    async def update_task(
        self,
        task_id: str,
        user_id: PydanticObjectId,
        schema: TaskUpdateSchema,
    ) -> Task:
        task = await TaskRepository.get_task_by_id(task_id, user_id)
        if not task:
            raise CustomException("Task not found", status_code=404)

        updated_task = await TaskRepository.update_task(task_id, user_id, schema)
        return updated_task

    async def delete_task(self, task_id: str, user_id: PydanticObjectId) -> None:
        deleted = await TaskRepository.delete_task(task_id, user_id)
        if not deleted:
            raise CustomException("Task not found", status_code=404)
