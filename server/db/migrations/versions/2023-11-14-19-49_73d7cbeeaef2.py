"""empty message

Revision ID: 73d7cbeeaef2
Revises: 27c53c66e746
Create Date: 2023-11-14 19:49:08.743415

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "73d7cbeeaef2"
down_revision = "27c53c66e746"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("ml_models", "layers")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "ml_models",
        sa.Column(
            "layers",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    # ### end Alembic commands ###
