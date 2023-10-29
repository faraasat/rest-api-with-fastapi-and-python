from pydantic import BaseModel, ConfigDict


class UserPostIn(BaseModel):
    body: str


class UserPost(UserPostIn):
    # so that returned values can be parsed to dict or object respectively
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int


class CommentIn(BaseModel):
    body: str
    post_id: int


class Comment(CommentIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int


class UserPostWithComments(BaseModel):
    post: UserPost
    comments: list[Comment]
