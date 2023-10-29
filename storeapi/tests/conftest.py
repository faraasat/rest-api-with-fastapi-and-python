# this is a fixture and a fixture is used to share the data
import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# from storeapi.routers.post import comment_table, post_table

os.environ["ENV_STATE"] = "test"

from storeapi.main import app  # noqa: E402
from storeapi.database import database, user_table  # noqa: E402


# "session" means run only once for the test session
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def client() -> Generator:
    yield TestClient(app)


# auto is to run on every test
@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:
    # post_table.clear()
    # comment_table.clear()

    # after every disconnect database will rollback as DB_FORCE_ROLLBACK is True
    await database.connect()
    yield
    await database.disconnect()


@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    async with AsyncClient(app=app, base_url=client.base_url) as ac:
        yield ac


@pytest.fixture()
async def registered_user(async_client: AsyncClient) -> dict:
    user_details = {"email": "test@example.net", "password": "1234"}

    await async_client.post("/register", json=user_details)

    query = user_table.select().where(user_table.c.email == user_details["email"])
    user = await database.fetch_one(query)
    user_details["id"] = user.id

    return user_details


@pytest.fixture()
async def logged_in_token(async_client: AsyncClient, registered_user: dict) -> str:
    response = await async_client.post("/token", json=registered_user)
    return response.json()["access_token"]
