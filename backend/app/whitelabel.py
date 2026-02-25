"""Griffin Gold — White-Label Manager.

Loads branding configuration for broker white-label deployments.
"""
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Default Griffin Gold branding
DEFAULT_BRANDING = {
    "broker_code": "",
    "broker_name": "Griffin Gold",
    "logo_url": "",
    "primary_color": "#D4AF37",
    "secondary_color": "#0f0f14",
    "accent_color": "#FFD700",
    "bot_name": "Griffin Gold",
    "welcome_message": "Welcome to Griffin Gold — AI-powered XAUUSD trading intelligence.",
    "broker_signup_url": "",
}

# ATFX preset
ATFX_BRANDING = {
    "broker_code": "atfx",
    "broker_name": "ATFX Gold AI",
    "logo_url": "",
    "primary_color": "#1a3c6d",
    "secondary_color": "#0d1b2a",
    "accent_color": "#4a90d9",
    "bot_name": "ATFX Gold AI",
    "welcome_message": "Welcome to ATFX Gold AI — powered by Griffin Gold.",
    "broker_signup_url": "https://www.atfx.com/register",
}

PRESETS = {"atfx": ATFX_BRANDING}


class WhiteLabelManager:
    """Manages white-label branding for broker deployments."""

    _cached_branding: Optional[dict] = None

    @classmethod
    async def get_branding(cls) -> dict:
        """Get active branding config. Checks DB first, then presets, then default."""
        if cls._cached_branding:
            return cls._cached_branding

        broker_code = settings.whitelabel_broker_code

        if not broker_code:
            cls._cached_branding = DEFAULT_BRANDING
            return cls._cached_branding

        # Check presets
        if broker_code in PRESETS:
            cls._cached_branding = PRESETS[broker_code]
            return cls._cached_branding

        # Try DB
        try:
            from app.database import async_session, WhiteLabelConfig
            from sqlalchemy import select

            async with async_session() as session:
                result = await session.execute(
                    select(WhiteLabelConfig).where(
                        WhiteLabelConfig.broker_code == broker_code
                    )
                )
                config = result.scalar_one_or_none()
                if config:
                    cls._cached_branding = {
                        "broker_code": config.broker_code,
                        "broker_name": config.broker_name,
                        "logo_url": config.logo_url or "",
                        "primary_color": config.primary_color,
                        "secondary_color": config.secondary_color,
                        "accent_color": config.accent_color,
                        "bot_name": config.bot_name,
                        "welcome_message": config.welcome_message or "",
                        "broker_signup_url": config.broker_signup_url or "",
                    }
                    return cls._cached_branding
        except Exception as e:
            logger.warning(f"Failed to load white-label from DB: {e}")

        cls._cached_branding = DEFAULT_BRANDING
        return cls._cached_branding

    @classmethod
    def clear_cache(cls):
        cls._cached_branding = None
