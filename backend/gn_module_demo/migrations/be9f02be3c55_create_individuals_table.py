"""create_individuals_table

Revision ID: be9f02be3c55
Revises: 2a0c9e4f3b7f
Create Date: 2026-01-22 09:49:30.109045

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "be9f02be3c55"
down_revision = "2a0c9e4f3b7f"
branch_labels = None
depends_on = None

SCHEMA_NAME = "gn_demo"


def upgrade():
    conn = op.get_bind()
    t_indiv = op.create_table(
        "t_individuals",
        sa.Column(
            "id_individual",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "name",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "cd_nom",
            sa.Integer(),
            sa.ForeignKey("taxonomie.taxref.cd_nom"),
            nullable=True,
        ),
        schema=SCHEMA_NAME,
    )

    op.execute(
        sa.insert(t_indiv).values(
            [
                {"id_individual": 1, "name": "John", "cd_nom": 2852},
                {"id_individual": 2, "name": "Jane", "cd_nom": 2962},
            ]
        )
    )


def downgrade():
    op.drop_table("t_individuals", schema=SCHEMA_NAME)
    #pass
