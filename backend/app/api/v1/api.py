"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
# from app.api.v1.chatbot import router as chatbot_router
from app.api.v1.system.ai_model import router as ai_model_router
from app.api.v1.system.mcp_server import router as mcp_server_router

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
# api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(ai_model_router)
api_router.include_router(mcp_server_router)
