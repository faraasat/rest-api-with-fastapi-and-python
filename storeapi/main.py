from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from storeapi.loggin_conf import configure_logging
from storeapi.database import database
from storeapi.routers.post import router as post_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await database.connect()
    logger.info("Database Connected")
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(post_router)
