import uuid
from collections.abc import Sequence

from pydantic import BaseModel
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession


class DefaultRepository[ModelType: SQLModel]:
    """
    Generic repository providing base CRUD operations for a SQLModel table.
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    def get(self, primary_key: uuid.UUID) -> ModelType | None:
        """
        Get an instance by its primary key.

        Args:
            primary_key (uuid.UUID): the primary key to look up.

        Returns:
            ModelType | None: the instance, or None if not found.
        """

        return self.session.get(self.model, primary_key)

    def list(self, filters: BaseModel | None = None) -> Sequence[ModelType]:
        """
        List instances, optionally filtered by equality on the given fields.

        Unknown fields on `filters` (not columns of the model) are silently ignored.

        Args:
            filters (BaseModel | None): fields to filter on, unset fields are ignored.

        Returns:
            Sequence[ModelType]: the matching instances.
        """

        statement = select(self.model)

        if filters is not None:
            for field, value in filters.model_dump(exclude_none=True).items():
                column = getattr(self.model, field, None)
                if column is not None:
                    statement = statement.where(column == value)

        return self.session.exec(statement).all()

    def create(self, **kwargs) -> ModelType:
        """
        Create and persist a new instance.

        Args:
            **kwargs: fields used to build the instance.

        Returns:
            ModelType: the created instance.
        """

        instance = self.model(**kwargs)

        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)

        return instance

    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """
        Update and persist fields on an existing instance.

        Args:
            instance (ModelType): the instance to update.
            **kwargs: fields to update.

        Returns:
            ModelType: the updated instance.
        """

        for field, value in kwargs.items():
            setattr(instance, field, value)

        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)

        return instance

    def delete(self, instance: ModelType) -> None:
        """
        Delete an instance.

        Args:
            instance (ModelType): the instance to delete.
        """

        self.session.delete(instance)
        self.session.commit()
