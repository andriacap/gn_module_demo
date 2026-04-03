"""add_geom_col

Revision ID: 40e1697000c1
Revises: e6fcc44d8fce
Create Date: 2026-02-23 15:33:42.234023

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.sql import table, column
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '40e1697000c1'
down_revision = 'e6fcc44d8fce'
branch_labels = None
depends_on = None

SCHEMA_NAME = "gn_demo"

def upgrade():
    conn = op.get_bind()

    t_indiv = table(
        "t_individuals",
        column("id_individual", sa.Integer),
        column("name", sa.String),
        column("cd_nom", sa.Integer),
        column("id_nomenclature_sex", sa.Integer),
        column("additional_data", JSONB),
        schema=SCHEMA_NAME,
    )

    # Ajouter la colonne
    op.add_column(
       "t_individuals",
        sa.Column(
            "geom_local",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=True
        ),
        schema=SCHEMA_NAME,
    )

def downgrade():
    conn = op.get_bind()
    op.drop_column("t_individuals", "geom_local", schema=SCHEMA_NAME)