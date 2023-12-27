import logging
from typing import Annotated
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
import sqlalchemy

from storeapi.models.post import (
    UserPost,
    UserPostIn,
    Comment,
    CommentIn,
    UserPostWithComments,
    PostLike,
    PostLikeIn,
    UserPostWithLikes,
)
from storeapi.database import comment_table, post_table, database, like_table
from storeapi.models.user import User
from storeapi.security import get_current_user
from storeapi.tasks import generate_and_add_to_post

router = APIRouter()


# post_table = {}
# comment_table = {}

logger = logging.getLogger(__name__)

# in this we are selecting the post table and creating a column likes
# the we are using select_from and joining the two tables ans then we are grouping based on post_table ids
select_post_and_like = (
    sqlalchemy.select(post_table, sqlalchemy.func.count(like_table.c.id).label("likes"))
    .select_from(post_table.outerjoin(like_table))
    .group_by(post_table.c.id)
)


async def find_post(post_id: int):
    logger.info(f"Find post with id {post_id}")

    query = post_table.select().where(post_table.c.id == post_id)

    logger.debug(query)

    return await database.fetch_one(query)


@router.post("/post", response_model=UserPost, status_code=201)
async def create_post(
    post: UserPostIn,
    current_user: Annotated[User, Depends(get_current_user)],
    background_task: BackgroundTasks,
    request: Request,
    prompt: str = None,
):
    logger.info("Getting a Post")

    data = {**post.model_dump(), "user_id": current_user.id}

    query = post_table.insert().values(
        {"body": data["body"], "user_id": data["user_id"]}
    )
    logger.debug(query)

    last_record_id = await database.execute(query)

    if prompt:
        background_task.add_task(
            generate_and_add_to_post,
            current_user.email,
            last_record_id,
            request.url_for("get_post_with_comments", post_id=last_record_id),
            database,
            prompt,
        )

    return {**data, "id": last_record_id}


class PostSorting(str, Enum):
    new = "new"
    old = "old"
    most_likes = "most_likes"


@router.get("/post", response_model=list[UserPostWithLikes])
async def get_post(
    sorting: PostSorting = PostSorting.new,
):  # https://api.com/post?sorting=new
    logger.info("Getting All Posts")

    # # can be done using match
    # match sorting:
    #     case PostSorting.new:
    #         query = select_post_and_like.order_by(post_table.c.id.desc())

    if sorting == PostSorting.new:
        query = select_post_and_like.order_by(post_table.c.id.desc())
    elif sorting == PostSorting.old:
        query = select_post_and_like.order_by(post_table.c.id.asc())
    elif sorting == PostSorting.most_likes:
        query = select_post_and_like.order_by(sqlalchemy.desc("likes"))

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

    # post = await find_post(post_id)
    query = select_post_and_like.where(post_table.c.id == post_id)
    logger.debug(query)

    post = await database.fetch_one(query)

    if not post:
        # logger.error(f"Post with post id {post_id} not found")
        raise HTTPException(status_code=404, detail="Post not found")

    return {"post": post, "comments": await get_comments_on_post(post_id)}


@router.post("/like", response_model=PostLike, status_code=201)
async def like_post(
    like: PostLikeIn, currentUser: Annotated[User, Depends(get_current_user)]
):
    logger.info("Liking Post")

    post = await find_post(like.post_id)

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    data = {**like.model_dump(), "user_id": currentUser.id}

    query = like_table.insert().values(data)
    logger.debug(query)

    last_record_id = await database.execute(query)

    return {**data, "id": last_record_id}
