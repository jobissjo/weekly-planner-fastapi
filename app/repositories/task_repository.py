from typing import List, Optional
from app.models.task import Task
from app.schemas.task_schema import TaskCreateSchema, TaskUpdateSchema
from beanie import PydanticObjectId


class TaskRepository:

    @staticmethod
    async def create_task(user_id: PydanticObjectId, schema: TaskCreateSchema) -> Task:
        task_data = schema.model_dump()
        task_data["user_id"] = user_id
        task = Task(**task_data)
        await task.insert()
        return task

    @staticmethod
    async def get_task_by_id(
        task_id: str, user_id: PydanticObjectId
    ) -> Optional[Task]:
        try:
            return await Task.find_one(
                Task.id == PydanticObjectId(task_id), Task.user_id == user_id
            )
        except Exception:
            return None

    @staticmethod
    async def list_tasks(
        user_id: PydanticObjectId,
        from_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Task]:
        query = [Task.user_id == user_id]
        if from_date:
            query.append(Task.date >= from_date)
        if end_date:
            query.append(Task.date <= end_date)

        # Sort tasks chronologically by date and startTime
        return await Task.find(*query).sort(Task.date, Task.startTime).to_list()

    @staticmethod
    async def update_task(
        task_id: str,
        user_id: PydanticObjectId,
        schema: TaskUpdateSchema,
    ) -> Optional[Task]:
        task = await TaskRepository.get_task_by_id(task_id, user_id)
        if not task:
            return None

        update_data = schema.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(task, key, val)

        await task.save()
        return task

    @staticmethod
    async def delete_task(task_id: str, user_id: PydanticObjectId) -> bool:
        task = await TaskRepository.get_task_by_id(task_id, user_id)
        if not task:
            return False
        await task.delete()
        return True

    @staticmethod
    async def get_tasks_by_title(
        title: str, user_id: PydanticObjectId
    ) -> List[Task]:
        import re
        regx = re.compile(rf".*{re.escape(title)}.*", re.IGNORECASE)
        return await Task.find(
            Task.user_id == user_id,
            {"title": regx}
        ).to_list()

