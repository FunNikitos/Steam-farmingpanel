"""Handlers package."""
from aiogram import Router

from . import start, accounts, steamguard, deals, giveaways, add_account, games, access, stats


def get_router() -> Router:
    """Get combined router with all handlers."""
    router = Router()

    # Include all sub-routers
    router.include_router(start.router)
    router.include_router(accounts.router)
    router.include_router(steamguard.router)
    router.include_router(deals.router)
    router.include_router(giveaways.router)
    router.include_router(add_account.router)
    router.include_router(games.router)
    router.include_router(access.router)
    router.include_router(stats.router)

    return router
