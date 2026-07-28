import factory
from auth.models import User
from faker import Faker

fake = Faker()


class UserFactory(factory.Factory):
    """
    Factory generating User instances with fake data.
    `hashed_password` is a fake placeholder, it does not match any known plaintext password.
    """

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"{fake.user_name()}_{n}")
    firstname = factory.Faker("first_name")
    lastname = factory.Faker("last_name")
    email = factory.Sequence(
        lambda n: f"{fake.user_name()}_{n}@{fake.free_email_domain()}"
    )
    hashed_password = factory.Faker("password")
