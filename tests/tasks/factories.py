import factory
from faker import Faker

from app.tasks.models import Task

fake = Faker()


class TaskFactory(factory.Factory):
    """
    Factory generating Task instances with fake data.
    `user_id` has no owner by default and must be passed explicitly.
    """

    class Meta:
        model = Task

    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("paragraph")
