import random
from typing import List, Optional
from app.models.motivation import Motivation
from beanie import PydanticObjectId


class MotivationRepository:

    @staticmethod
    async def create_motivation(
        title: str, content: str, is_active: bool = True
    ) -> Motivation:
        motivation = Motivation(title=title, content=content, is_active=is_active)
        await motivation.insert()
        return motivation

    @staticmethod
    async def get_motivation_by_id(motivation_id: str) -> Optional[Motivation]:
        try:
            return await Motivation.get(PydanticObjectId(motivation_id))
        except Exception:
            return None

    @staticmethod
    async def list_all_motivations() -> List[Motivation]:
        # Return all sorted by created_at descending
        return await Motivation.find_all().sort("-created_at").to_list()

    @staticmethod
    async def get_random_active_motivation() -> Optional[Motivation]:
        count = await Motivation.find(Motivation.is_active == True).count()
        if count == 0:
            return None
        random_index = random.randint(0, count - 1)
        return (
            await Motivation.find(Motivation.is_active == True)
            .skip(random_index)
            .limit(1)
            .first_or_none()
        )

    @staticmethod
    async def update_motivation(
        motivation_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Motivation]:
        motivation = await MotivationRepository.get_motivation_by_id(motivation_id)
        if not motivation:
            return None

        if title is not None:
            motivation.title = title
        if content is not None:
            motivation.content = content
        if is_active is not None:
            motivation.is_active = is_active

        await motivation.save()
        return motivation

    @staticmethod
    async def delete_motivation(motivation_id: str) -> bool:
        motivation = await MotivationRepository.get_motivation_by_id(motivation_id)
        if not motivation:
            return False
        await motivation.delete()
        return True
