from fastapi import APIRouter
from api.system import router as system_router
from api.taxonomy import router as taxonomy_router
from api.manufacturers import router as manufacturers_router
from api.models import router as models_router
from api.crawler import router as crawler_router

api_router = APIRouter()

# Register sub-routers
api_router.include_router(system_router, tags=["System"])
api_router.include_router(taxonomy_router, tags=["Taxonomy"])
api_router.include_router(manufacturers_router, tags=["Manufacturers"])
api_router.include_router(models_router, tags=["Models"])
api_router.include_router(crawler_router, tags=["Crawler"])
