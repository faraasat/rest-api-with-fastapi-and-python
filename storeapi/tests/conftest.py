# this is a fixture and a fixture is used to share the data
import os
from typing import AsyncGenerator, Generator

from unittest.mock import Mock, AsyncMock
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, Request, Response

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
async def confirmed_user(registered_user: dict) -> dict:
    query = (
        user_table.update()
        .where(user_table.c.email == registered_user["email"])
        .values(confirmed=True)
    )

    await database.execute(query)

    return registered_user


@pytest.fixture()
async def logged_in_token(async_client: AsyncClient, confirmed_user: dict) -> str:
    response = await async_client.post("/token", json=confirmed_user)
    return response.json()["access_token"]


@pytest.fixture(autouse=True)
def mock_httpx(mocker):
    mocked_client = mocker.patch("storeapi.tasks.httpx.AsyncClient")

    mocked_async_client = Mock()
    response = Response(200, content="", request=Request("POST", "//"))

    mocked_async_client.post = AsyncMock(return_value=response)
    mocked_client.return_value.__aenter__.return_value = mocked_async_client

    return mocked_async_client
