"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.alerts import events_router, rules_router
from app.modules.audit import router as audit_router
from app.modules.auth import router as auth_router
from app.modules.equipment import router as equipment_router
from app.modules.installations import router as installations_router
from app.modules.measurements import router as measurements_router
from app.modules.reports import router as reports_router


router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(installations_router)
router.include_router(equipment_router)
router.include_router(measurements_router)
router.include_router(rules_router)
router.include_router(events_router)
router.include_router(reports_router)
router.include_router(audit_router)
