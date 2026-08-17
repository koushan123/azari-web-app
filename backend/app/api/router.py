from fastapi import APIRouter

from backend.app.api.routes import auth, health, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(users.router, tags=["users"])

