"""Handlers package."""
from aiogram import Router

from . import start, accounts, steamguard, deals, giveaways


def get_router() -> Router:
    """Get combined router with all handlers."""
    router = Router()

    # Include all sub-routers
    router.include_router(start.router)
    router.include_router(accounts.router)
    router.include_router(steamguard.router)
    router.include_router(deals.router)
    router.include_router(giveaways.router)

    return router
