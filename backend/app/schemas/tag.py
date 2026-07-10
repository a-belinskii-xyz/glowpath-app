import uuid

from pydantic import BaseModel


class TagPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    group_id: uuid.UUID


class TagGroupPublic(BaseModel):
    id: uuid.UUID
    slug: str
    label: str
    sort_order: int
    tags: list[TagPublic]


class TagGroupListResponse(BaseModel):
    items: list[TagGroupPublic]
