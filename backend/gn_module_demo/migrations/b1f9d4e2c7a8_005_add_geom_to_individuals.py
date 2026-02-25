"""add geom geometry column to individuals

Revision ID: b1f9d4e2c7a8
Revises: 8c1a2b3c4d5e
Create Date: 2026-02-23 00:00:00.000000

"""

from alembic import op
from geoalchemy2 import Geometry
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b1f9d4e2c7a8"
down_revision = "8c1a2b3c4d5e"
branch_labels = None
depends_on = None

SCHEMA_NAME = "gn_demo"
TABLE_NAME = "t_individuals"
COLUMN_NAME = "geom"
INDEX_NAME = "ix_gn_demo_t_individuals_geom"


def upgrade():
    op.add_column(
        TABLE_NAME,
        sa.Column(
            COLUMN_NAME,
            Geometry("GEOMETRY", srid=4326),
            nullable=True,
        ),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        [COLUMN_NAME],
        unique=False,
        schema=SCHEMA_NAME,
        postgresql_using="gist",
    )


def downgrade():
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME, schema=SCHEMA_NAME)
    op.drop_column(TABLE_NAME, COLUMN_NAME, schema=SCHEMA_NAME)
