import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends

from storeapi.models.post import (
    UserPost,
    UserPostIn,
    Comment,
    CommentIn,
    UserPostWithComments,
)
from storeapi.database import comment_table, post_table, database
from storeapi.models.user import User
from storeapi.security import get_current_user

router = APIRouter()


# post_table = {}
# comment_table = {}

logger = logging.getLogger(__name__)


async def find_post(post_id: int):
    logger.info(f"Find post with id {post_id}")

    query = post_table.select().where(post_table.c.id == post_id)

    logger.debug(query)

    return await database.fetch_one(query)


@router.post("/post", response_model=UserPost, status_code=201)
async def create_post(
    post: UserPostIn, current_user: Annotated[User, Depends(get_current_user)]
):
    logger.info("Getting a Post")

    data = {**post.model_dump(), "user_id": current_user.id}

    query = post_table.insert().values(
        {"body": data["body"], "user_id": data["user_id"]}
    )
    logger.debug(query)

    last_record_id = await database.execute(query)

    return {**data, "id": last_record_id}


@router.get("/post", response_model=list[UserPost])
async def get_post():
    logger.info("Getting All Posts")

    query = post_table.select()

    logger.debug(query)

    return await database.fetch_all(query)


@router.post("/comment", response_model=Comment, status_code=201)
async def create_comment(
    comment: CommentIn, current_user: Annotated[User, Depends(get_current_user)]
):
    logger.info("Creating Comment")

    post = await find_post(comment.post_id)

    if not post:
        # logger.error(f"Post with id {comment.post_id} not found")
        raise HTTPException(status_code=404, detail="Post not found")

    data = {**comment.model_dump(), "user_id": current_user.id}
    query = comment_table.insert().values(data)

    logger.debug(query)

    last_recorded_id = await database.execute(query)

    return {**data, "id": last_recorded_id}


@router.get("/post/{post_id}/comment", response_model=list[Comment])
async def get_comments_on_post(post_id: int):
    logger.info("Getting Comments on Post")

    query = comment_table.select().where(comment_table.c.post_id == post_id)
    logger.debug(query)

    return await database.fetch_all(query)


@router.get("/post/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comments(post_id: int):
    logger.info("Getting Post and its Comments")

    post = await find_post(post_id)
    if not post:
        # logger.error(f"Post with post id {post_id} not found")
        raise HTTPException(status_code=404, detail="Post not found")

    return {"post": post, "comments": await get_comments_on_post(post_id)}
