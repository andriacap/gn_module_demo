"""add additional_data

Revision ID: a5ba14587fd1
Revises: abe9f02be3c5
Create Date: 2026-01-23 09:56:14.977771

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "a5ba14587fd1"
down_revision = "abe9f02be3c5"
branch_labels = None
depends_on = None

SCHEMA_NAME = "gn_demo_pnv"


def upgrade():
    conn = op.get_bind()

    op.add_column(
        "t_individuals",
        sa.Column("additional_data", JSONB, nullable=True),
        schema=SCHEMA_NAME,
    ),

    t_indiv = table(
        "t_individuals",
        column("id_individual", sa.Integer),
        column("name", sa.String),
        column("cd_nom", sa.Integer),
        column("additional_data", JSONB),
        schema=SCHEMA_NAME,
    )

    op.execute(
        sa.insert(t_indiv).values(
            [
                {
                    "id_individual": 3,
                    "name": "Bouqui",
                    "cd_nom": 2852,
                    "additional_data": {"collier": "rouge", "taille_cm": 45},
                },
                {
                    "id_individual": 4,
                    "name": "Crâned'oeuf",
                    "cd_nom": 2962,
                    "additional_data": {"collier": "vert/rouge", "taille_cm": 40.2},
                },
            ]
        )
        # sa.text (
        #     f"""
        #     INSERT INTO {SCHEMA_NAME}.{TABLE_NAME}
        #     VALUES (1,'Jojo',2852,'{{"annee_naissance": 2008,"sexe":"m"}}'), (2,'Marie',2852,'{{"annee_naissance": 2005,"sexe":"f"}}'), (3,'Pierre',2962,'{{"annee_naissance": 1998}}'), (4,'Sophie',2852,'{{"annee_naissance": 2001,"sexe":"f"}}'), (5,'Luc',2962,'{{"annee_naissance": 1999}}'), (6,'Claire',2852,'{{"annee_naissance": 1997}}'), (7,'Thomas',2852,'{{"annee_naissance": 1996}}'), (8,'Emma',2852,'{{"annee_naissance": 1994}}'), (9,'Hugo',2852,'{{"annee_naissance": 1993}}'), (10,'Léa',2962,'{{"annee_naissance": 1987}}')
        #     """)
    )


def downgrade():
    # op.drop_table("t_individuals", schema=SCHEMA_NAME)
    pass
