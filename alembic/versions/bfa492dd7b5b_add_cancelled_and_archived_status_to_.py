"""add cancelled and archived status to task

Revision ID: bfa492dd7b5b
Revises: f132464c5630
Create Date: 2026-08-01 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bfa492dd7b5b"
down_revision: str | Sequence[str] | None = "f132464c5630"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Adding a value to a PostgreSQL native ENUM cannot be done through
    autogenerate (it emits nothing) and `ALTER TYPE ... ADD VALUE` cannot run
    inside the transaction Alembic normally wraps a migration in, hence the
    `autocommit_block`. SQLite (used in tests) emulates enums as a
    VARCHAR + CHECK constraint, so it needs no equivalent statement here;
    guard on dialect so this migration stays a no-op there.
    """

    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE status ADD VALUE IF NOT EXISTS 'CANCELLED'")
            op.execute("ALTER TYPE status ADD VALUE IF NOT EXISTS 'ARCHIVED'")


def downgrade() -> None:
    """Downgrade schema.

    PostgreSQL does not support removing a value from a native ENUM type.
    Reverting would require rebuilding the type (create a new one without
    'CANCELLED'/'ARCHIVED', cast the column over, drop the old type), which
    is only safe if no row currently uses these statuses. Not implemented.
    """

    raise NotImplementedError(
        "Cannot remove values from the 'status' PostgreSQL enum type; "
        "downgrading this revision requires a manual, data-aware migration."
    )
