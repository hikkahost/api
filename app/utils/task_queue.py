import asyncio
import logging
import time
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Dict, Optional
from uuid import uuid4

from app.config import SERVER
from app.src.caddy import update_password
from app.src.container import (
    create,
    stop,
    start,
    restart,
    recreate,
    execute,
    remove,
)


logger = logging.getLogger(__name__)


class TaskStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType:
    CREATE = "create"
    ACTION = "action"
    EXEC = "exec"
    REMOVE = "remove"
    UPDATE_PASSWORD = "update_password"


@dataclass
class TaskRecord:
    id: str
    task_type: str
    payload: Dict[str, Any]
    status: str = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class QueueService:
    def __init__(self):
        self._queue: Optional[asyncio.Queue] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._tasks: Dict[str, TaskRecord] = {}

    def _ensure_worker(self) -> None:
        if self._queue is None:
            self._queue = asyncio.Queue()
        if self._worker_task is None or self._worker_task.done():
            loop = asyncio.get_running_loop()
            self._worker_task = loop.create_task(self._worker())

    async def _run_blocking(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def add_task(self, task_type: str, payload: Dict[str, Any]) -> str:
        self._ensure_worker()
        task_id = str(uuid4())
        self._tasks[task_id] = TaskRecord(
            id=task_id,
            task_type=task_type,
            payload=payload,
        )
        await self._queue.put(task_id)
        return task_id

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        return {
            "task_id": task.id,
            "status": task.status,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "result": task.result,
            "error": task.error,
        }

    async def _worker(self) -> None:
        while True:
            task_id = await self._queue.get()
            try:
                await self._process_task(task_id)
            finally:
                self._queue.task_done()

    async def _process_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        task.status = TaskStatus.PROCESSING
        task.updated_at = time.time()
        try:
            task.result = await self._execute_task(task)
            task.status = TaskStatus.COMPLETED
        except Exception as exc:
            logger.error("Task %s failed: %s", task_id, exc, exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(exc)
        finally:
            task.updated_at = time.time()

    async def _execute_task(self, task: TaskRecord) -> Dict[str, Any]:
        payload = task.payload or {}
        if task.task_type == TaskType.CREATE:
            await self._run_blocking(
                create,
                payload["port"],
                payload["name"],
                payload.get("userbot"),
                payload.get("password"),
            )
            return {"message": "created"}
        if task.task_type == TaskType.ACTION:
            action_type = payload["type"]
            name = payload["name"]
            actions = {
                "start": start,
                "stop": stop,
                "restart": restart,
                "recreate": recreate,
            }
            action = actions.get(action_type)
            if action is None:
                raise ValueError("Unknown action")
            action_output = await self._run_blocking(action, name)
            return action_output or {"message": "action completed"}
        if task.task_type == TaskType.EXEC:
            result = await self._run_blocking(
                execute, payload["name"], payload["command"]
            )
            return {"exec": result}
        if task.task_type == TaskType.REMOVE:
            result = await self._run_blocking(remove, payload["name"])
            return {"remove": result}
        if task.task_type == TaskType.UPDATE_PASSWORD:
            result = await self._run_blocking(
                update_password, payload["name"], SERVER, payload["password"]
            )
            return {"update": result}
        raise ValueError("Unknown task type")


queue_service = QueueService()
