from pydantic import BaseModel
from typing import List


class TaskBase(BaseModel):
    name: str
    description: str
    priority: int


class TaskResponse(TaskBase):
    id: str


class AllTaskResponse(BaseModel):
    tasks: List[TaskResponse]
