from typing import List

from fastapi import APIRouter, Depends

from app.core.permissions import any_user_role, only_admin
from app.models import User
from app.models.announcement import Announcement
from app.schemas.announcement_schema import (
    AnnouncementCreateSchema,
    AnnouncementResponse,
    AnnouncementUpdateSchema,
)
from app.schemas.common_schema import BaseResponse
from app.utils.common import CustomException

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("", response_model=BaseResponse[List[AnnouncementResponse]])
async def list_active_announcements(
    current_user: User = Depends(any_user_role),
):
    """
    List all active announcements for users.
    """
    announcements = (
        await Announcement.find(Announcement.is_active == True)
        .sort(-Announcement.created_at)
        .to_list()
    )
    return BaseResponse(
        status="success",
        message="Active announcements retrieved successfully",
        data=[AnnouncementResponse.model_validate(a) for a in announcements],
    )


@router.get("/admin", response_model=BaseResponse[List[AnnouncementResponse]])
async def list_all_announcements_admin(
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] List all announcements (both active and inactive).
    """
    announcements = (
        await Announcement.find_all().sort(-Announcement.created_at).to_list()
    )
    return BaseResponse(
        status="success",
        message="All announcements retrieved successfully",
        data=[AnnouncementResponse.model_validate(a) for a in announcements],
    )


@router.post("/admin", response_model=BaseResponse[AnnouncementResponse])
async def create_announcement_admin(
    data: AnnouncementCreateSchema,
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Create a new announcement.
    """
    announcement = Announcement(
        title=data.title,
        description=data.description,
        banner_url=data.banner_url,
        is_active=data.is_active,
    )
    await announcement.insert()
    return BaseResponse(
        status="success",
        message="Announcement created successfully",
        data=AnnouncementResponse.model_validate(announcement),
    )


@router.patch("/admin/{id}", response_model=BaseResponse[AnnouncementResponse])
async def update_announcement_admin(
    id: str,
    data: AnnouncementUpdateSchema,
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Update an existing announcement.
    """
    from beanie import PydanticObjectId

    try:
        announcement = await Announcement.get(PydanticObjectId(id))
    except Exception:
        raise CustomException("Announcement not found", status_code=404)

    if not announcement:
        raise CustomException("Announcement not found", status_code=404)

    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(announcement, key, val)

    await announcement.save()
    return BaseResponse(
        status="success",
        message="Announcement updated successfully",
        data=AnnouncementResponse.model_validate(announcement),
    )


@router.delete("/admin/{id}", response_model=BaseResponse[None])
async def delete_announcement_admin(
    id: str,
    current_user: User = Depends(only_admin),
):
    """
    [ADMIN ONLY] Delete an announcement.
    """
    from beanie import PydanticObjectId

    try:
        announcement = await Announcement.get(PydanticObjectId(id))
    except Exception:
        raise CustomException("Announcement not found", status_code=404)

    if not announcement:
        raise CustomException("Announcement not found", status_code=404)

    await announcement.delete()
    return BaseResponse(
        status="success",
        message="Announcement deleted successfully",
        data=None,
    )
