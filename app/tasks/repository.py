from app.core.repository import DefaultRepository

from .models import Task


class TaskRepository(DefaultRepository[Task]):
    """
    Repository for the Task model.
    """

    model = Task
