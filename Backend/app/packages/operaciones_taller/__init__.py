"""PUDS package for CU09, CU10, CU11, CU16 and CU23."""

from fastapi import APIRouter

from .router import realtime_router, router as workshop_router


router = APIRouter()
router.include_router(workshop_router)
router.include_router(realtime_router)

__all__ = ["router"]
