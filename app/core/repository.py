from sqlmodel import Session


class DefaultRepository:
    """
    Repository of the model User, used to interface the DB.
    """

    model: ...

    def __init__(self, db: Session):
        self.db = db

    def create(self, *args, **kwargs):

        instance = self.model(*args, **kwargs)

        # publish to database

        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)

        return instance
