"""add individual tags referential and m2m association

Revision ID: c9e4b7a1d2f0
Revises: b1f9d4e2c7a8
Create Date: 2026-02-23 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c9e4b7a1d2f0"
down_revision = "b1f9d4e2c7a8"
branch_labels = None
depends_on = None

SCHEMA_NAME = "gn_demo"
TAGS_TABLE = "bib_individual_tags"
COR_TABLE = "cor_individual_tag"


def upgrade():
    op.create_table(
        TAGS_TABLE,
        sa.Column("id_tag", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code_tag", sa.String(length=50), nullable=False),
        sa.Column("label_tag", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("code_tag", name="uq_gn_demo_bib_individual_tags_code_tag"),
        schema=SCHEMA_NAME,
    )

    op.create_table(
        COR_TABLE,
        sa.Column(
            "id_individual",
            sa.Integer(),
            sa.ForeignKey("gn_demo.t_individuals.id_individual", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "id_tag",
            sa.Integer(),
            sa.ForeignKey("gn_demo.bib_individual_tags.id_tag", ondelete="CASCADE"),
            primary_key=True,
        ),
        schema=SCHEMA_NAME,
    )

    op.execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA_NAME}.{TAGS_TABLE} (code_tag, label_tag)
            VALUES
                ('MAMM', 'Mammifere'),
                ('BIRD', 'Oiseau'),
                ('REPT', 'Reptile'),
                ('RARE', 'Espece rare')
            ON CONFLICT (code_tag) DO NOTHING
            """
        )
    )


def downgrade():
    op.drop_table(COR_TABLE, schema=SCHEMA_NAME)
    op.drop_table(TAGS_TABLE, schema=SCHEMA_NAME)
