from src.schemas.task_schema import AllTaskResponse, TaskResponse, TaskBase
from src.services.task import task_service
from typing import Dict


task = task_service.task_model()

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "",
)
async def get_all_tasks() -> AllTaskResponse:
    return await task.task_getall_model()


@router.post("", status_code=201)
async def add_task(request: TaskBase):
    await task.task_add_model(request)


@router.delete("")
async def delete_all_task() -> int:
    return await task.task_deleteall_model()


@router.get("/{task_id}")
async def get_one_tasks(task_id) -> TaskResponse:
    return await task.task_getone_model(task_id)


@router.put("/{task_id}", status_code=204)
async def update_task(request: TaskBase, task_id: str):
    await task.task_update_model(request, task_id)


@router.delete(
    "/{task_id}",
)
async def delete_task(task_id):
    return await task.task_delete_model(task_id)
