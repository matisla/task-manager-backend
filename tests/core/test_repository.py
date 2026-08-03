import uuid

from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tasks.models import Task
from app.tasks.repository import TaskRepository

from ..tasks.factories import TaskFactory


class UnknownFieldFilter(BaseModel):
    """
    Filter carrying a field that is not a column on Task, used to exercise
    DefaultRepository.list()'s documented behavior: unknown fields are silently ignored.
    """

    not_a_column: str | None = None
    user_id: uuid.UUID | None = None


class TestDefaultRepositoryList:
    async def test_list_ignores_unknown_filter_field(self, session: AsyncSession):

        owner_id = uuid.uuid4()
        tasks = TaskFactory.create_batch(2, user_id=owner_id)
        session.add_all(tasks)
        await session.commit()

        repository = TaskRepository(session)

        filters = UnknownFieldFilter(not_a_column="does-not-exist", user_id=owner_id)
        results = await repository.list(filters)

        assert {task.id for task in results} == {task.id for task in tasks}
        assert all(isinstance(task, Task) for task in results)
