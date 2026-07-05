from typing import List, Optional

from beanie import PydanticObjectId

from app.core.events import event_manager
from app.core.logger_config import logger as default_logger
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task_schema import TaskCreateSchema, TaskResponse, TaskUpdateSchema
from app.services.streak_service import StreakService
from app.utils.common import CustomException


class TaskService:
    def __init__(self, logger=None):
        self.logger = logger or default_logger
        self.streak_service = StreakService()

    async def create_task(
        self, user_id: PydanticObjectId, schema: TaskCreateSchema
    ) -> Task:
        if schema.status == "completed" and not schema.completedDate:
            schema.completedDate = schema.date
        task = await TaskRepository.create_task(user_id, schema)
        if task.status == "completed":
            await self.streak_service.update_streak_on_task_status_change(
                user_id, task.date, True
            )
        try:
            task_data = TaskResponse.model_validate(task).model_dump(mode="json")
            await event_manager.publish(str(user_id), "task_created", task_data)
        except Exception as e:
            self.logger.error(f"Failed to publish task_created event: {e}")
        return task

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

        old_status = task.status
        old_date = task.date

        target_status = schema.status if schema.status is not None else task.status
        target_date = schema.date if schema.date is not None else task.date

        if target_status == "completed":
            if schema.completedDate is not None:
                pass
            elif getattr(task, "completedDate", None) is None:
                schema.completedDate = target_date
        else:
            if schema.status is not None:
                schema.completedDate = None

        updated_task = await TaskRepository.update_task(task_id, user_id, schema)

        if not updated_task:
            raise CustomException("Task not found", status_code=404)

        # Trigger streak recalculation if completed status or date changes
        if (
            old_status == "completed"
            or updated_task.status == "completed"
            or old_date != updated_task.date
        ):
            await self.streak_service.recalculate_user_streak(user_id)

        try:
            task_data = TaskResponse.model_validate(updated_task).model_dump(mode="json")
            await event_manager.publish(str(user_id), "task_updated", task_data)
        except Exception as e:
            self.logger.error(f"Failed to publish task_updated event: {e}")

        return updated_task

    async def delete_task(self, task_id: str, user_id: PydanticObjectId) -> None:
        task = await TaskRepository.get_task_by_id(task_id, user_id)
        if not task:
            raise CustomException("Task not found", status_code=404)

        old_status = task.status

        deleted = await TaskRepository.delete_task(task_id, user_id)
        if not deleted:
            raise CustomException("Task not found", status_code=404)

        if old_status == "completed":
            await self.streak_service.recalculate_user_streak(user_id)

        try:
            from app.core.events import event_manager
            await event_manager.publish(str(user_id), "task_deleted", {"id": task_id})
        except Exception as e:
            self.logger.error(f"Failed to publish task_deleted event: {e}")

    async def get_tasks_by_title(
        self, title: str, user_id: PydanticObjectId
    ) -> List[Task]:
        return await TaskRepository.get_tasks_by_title(title, user_id)
