from typing import List
from app.models.motivation import Motivation
from app.repositories.motivation_repository import MotivationRepository
from app.schemas.motivation_schema import MotivationCreateSchema, MotivationUpdateSchema
from app.utils.common import CustomException
from app.core.logger_config import logger as default_logger


class MotivationService:

    def __init__(self, logger=None):
        self.logger = logger or default_logger

    async def create_motivation(self, schema: MotivationCreateSchema) -> Motivation:
        return await MotivationRepository.create_motivation(
            title=schema.title, content=schema.content, is_active=schema.is_active
        )

    async def get_motivation_by_id(self, motivation_id: str) -> Motivation:
        motivation = await MotivationRepository.get_motivation_by_id(motivation_id)
        if not motivation:
            raise CustomException("Motivation not found", status_code=404)
        return motivation

    async def list_all_motivations(self) -> List[Motivation]:
        return await MotivationRepository.list_all_motivations()

    async def get_random_active_motivation(self) -> Motivation:
        motivation = await MotivationRepository.get_random_active_motivation()
        if not motivation:
            raise CustomException("No active motivations found", status_code=404)
        return motivation

    async def update_motivation(
        self, motivation_id: str, schema: MotivationUpdateSchema
    ) -> Motivation:
        # Check existence first
        motivation = await MotivationRepository.get_motivation_by_id(motivation_id)
        if not motivation:
            raise CustomException("Motivation not found", status_code=404)

        updated_motivation = await MotivationRepository.update_motivation(
            motivation_id=motivation_id,
            title=schema.title,
            content=schema.content,
            is_active=schema.is_active,
        )
        return updated_motivation

    async def delete_motivation(self, motivation_id: str) -> None:
        deleted = await MotivationRepository.delete_motivation(motivation_id)
        if not deleted:
            raise CustomException("Motivation not found", status_code=404)
