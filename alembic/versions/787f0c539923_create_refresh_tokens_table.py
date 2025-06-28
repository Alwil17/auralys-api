"""create refresh tokens table

Revision ID: 787f0c539923
Revises: 4f4e48e81baf
Create Date: 2025-06-27 18:07:35.109730

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "787f0c539923"
down_revision: Union[str, Sequence[str], None] = "4f4e48e81baf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
