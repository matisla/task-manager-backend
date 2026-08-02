"""apply naming convention and add user updated_at

Revision ID: 375db4a72742
Revises: bfa492dd7b5b
Create Date: 2026-08-02 22:46:48.021968

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "375db4a72742"
down_revision: str | Sequence[str] | None = "bfa492dd7b5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Adds `User.updated_at` (new field from `TimestampMixin`) and makes
    `User.created_at` NOT NULL (it is now populated by a `default_factory`,
    same as `Task.created_at` already was).

    Note: the new `SQLModel.metadata.naming_convention` (see `app/database.py`)
    only applies to constraints created from now on; autogenerate does not
    retroactively detect/rename this database's existing constraints (created
    without an explicit naming convention, so Postgres assigned its own
    default names such as `user_pkey`, `user_email_key`, `task_user_id_fkey`).
    Renaming them to match the new convention would need a separate, manual
    migration and is not included here.
    """

    op.add_column("user", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.alter_column(
        "user",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.alter_column(
        "user",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
    )
    op.drop_column("user", "updated_at")
