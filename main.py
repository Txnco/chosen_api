from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from database import Base, engine
from routers.auth import auth_router
from routers.user import user_router
from routers.questionnaire import quest_router
from models.role import Role
from models.user import User
from models.questionnaire import UserQuestionnaire
import logging

app = FastAPI()
Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(quest_router)

# ✅ Setup basic logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_logger")

# ✅ Middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    logger.info(f"➡️ Incoming request: {request.method} {request.url.path}")
    logger.info(f"🔸 Body: {body.decode('utf-8') if body else '<empty>'}")
    response = await call_next(request)
    logger.info(f"⬅️ Response status: {response.status_code}")
    return response
