"""Branding API for white-label frontend."""
from fastapi import APIRouter

from app.whitelabel import WhiteLabelManager

router = APIRouter(prefix="/api", tags=["branding"])


@router.get("/branding")
async def get_branding():
    return await WhiteLabelManager.get_branding()
