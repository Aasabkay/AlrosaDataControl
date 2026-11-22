from fastapi import APIRouter

from app.api.endpoints.imports import imports_router
from app.api.endpoints.sources import sources_router

main_router = APIRouter()

main_router.include_router(imports_router)
main_router.include_router(sources_router)