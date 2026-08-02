import uuid

from pydantic import BaseModel
from sqlmodel import Session
from tasks.models import Task
from tasks.repositories import TaskRepository

from ..tasks.factories import TaskFactory


class UnknownFieldFilter(BaseModel):
    """
    Filter carrying a field that is not a column on Task, used to exercise
    DefaultRepository.list()'s documented behavior: unknown fields are silently ignored.
    """

    not_a_column: str | None = None
    user_id: uuid.UUID | None = None


class TestDefaultRepositoryList:

    def test_list_ignores_unknown_filter_field(self, session: Session):

        owner_id = uuid.uuid4()
        tasks = TaskFactory.create_batch(2, user_id=owner_id)
        session.add_all(tasks)
        session.commit()

        repository = TaskRepository(session)

        filters = UnknownFieldFilter(not_a_column="does-not-exist", user_id=owner_id)
        results = repository.list(filters)

        assert {task.id for task in results} == {task.id for task in tasks}
        assert all(isinstance(task, Task) for task in results)
