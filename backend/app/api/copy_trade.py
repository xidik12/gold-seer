"""Copy trading API."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/copy-trade", tags=["copy_trade"])


@router.get("/status")
async def get_copy_trade_status():
    return {"active": False, "message": "Copy trading coming soon"}
