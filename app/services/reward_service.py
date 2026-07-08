from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId

from app.models.reward import Reward
from app.utils.common import CustomException


class RewardService:
    @staticmethod
    async def get_default_generic_rewards() -> List[dict]:
        return [
            {
                "title": "Cheat meal",
                "description": "Order your favorite pizza, burger, or dessert",
                "is_generic": True,
            },
            {
                "title": "Play video games",
                "description": "1 hour of guilt-free video gaming",
                "is_generic": True,
            },
            {
                "title": "Watch a movie",
                "description": "Watch that new movie on your list",
                "is_generic": True,
            },
            {
                "title": "Buy a new book",
                "description": "Get that book you've been wanting to read",
                "is_generic": True,
            },
            {
                "title": "Spa or massage",
                "description": "A relaxing bath or a professional massage",
                "is_generic": True,
            },
            {
                "title": "Sleep early",
                "description": "Go to bed early and get 8+ hours of sleep",
                "is_generic": True,
            },
        ]

    async def list_rewards(self, user_id: PydanticObjectId) -> List[Reward]:
        # Seed generic rewards if none exist in the database
        generics = await Reward.find(Reward.is_generic == True).to_list()
        if not generics:
            default_rewards = await self.get_default_generic_rewards()
            for r in default_rewards:
                new_r = Reward(**r)
                await new_r.insert()
            generics = await Reward.find(Reward.is_generic == True).to_list()

        user_rewards = await Reward.find(Reward.user_id == user_id).to_list()
        return user_rewards + generics

    async def create_reward(
        self, user_id: PydanticObjectId, title: str, description: Optional[str]
    ) -> Reward:
        reward = Reward(
            user_id=user_id,
            title=title,
            description=description,
            is_favorite=False,
            is_generic=False,
        )
        await reward.insert()
        return reward

    async def delete_reward(self, user_id: PydanticObjectId, reward_id: str) -> None:
        reward = await Reward.get(reward_id)
        if not reward:
            raise CustomException("Reward not found", 404)
        if reward.user_id != user_id:
            raise CustomException("Not authorized to delete this reward", 403)
        if reward.is_generic:
            raise CustomException("Cannot delete generic rewards", 400)
        await reward.delete()

    async def select_favorite_reward(
        self, user_id: PydanticObjectId, reward_id: str
    ) -> Reward:
        target_reward = await Reward.get(reward_id)
        if not target_reward:
            raise CustomException("Reward not found", 404)

        # Deactivate all other favorite rewards for this user
        user_favorites = await Reward.find(
            Reward.user_id == user_id, Reward.is_favorite == True
        ).to_list()
        for f in user_favorites:
            f.is_favorite = False
            await f.save()

        if target_reward.is_generic:
            # Check if user already copied it or create a new user-specific favorite
            existing_user_copy = await Reward.find(
                Reward.user_id == user_id, Reward.title == target_reward.title
            ).first_or_none()

            if existing_user_copy:
                existing_user_copy.is_favorite = True
                existing_user_copy.updated_at = datetime.utcnow()
                await existing_user_copy.save()
                return existing_user_copy
            else:
                new_reward = Reward(
                    user_id=user_id,
                    title=target_reward.title,
                    description=target_reward.description,
                    is_favorite=True,
                    is_generic=False,
                )
                await new_reward.insert()
                return new_reward
        else:
            if target_reward.user_id != user_id:
                raise CustomException("Not authorized", 403)

            target_reward.is_favorite = True
            target_reward.updated_at = datetime.utcnow()
            await target_reward.save()
            return target_reward

    async def get_favorite_reward(self, user_id: PydanticObjectId) -> Optional[Reward]:
        fav = await Reward.find(
            Reward.user_id == user_id, Reward.is_favorite == True
        ).first_or_none()
        return fav
