"""add id_nomenclature_sex

Revision ID: ae6fcc44d8fc
Revises: a5ba14587fd1
Create Date: 2026-02-09 17:04:22.904162

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'ae6fcc44d8fc'
down_revision = 'a5ba14587fd1'
branch_labels = None
depends_on = None

SCHEMA_NAME = "gn_demo_pnv"

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

    # Supprimer toutes les entrées existantes
    op.execute(sa.delete(t_indiv))

    # Ajouter la colonne
    op.add_column(
       "t_individuals",
        sa.Column(
            "id_nomenclature_sex",
            sa.Integer,
            nullable=False,
            default="ref_nomenclatures.get_default_nomenclature_value('SEXE'::character varying)"
        ),
        schema=SCHEMA_NAME,
    )

    # Ajouter la contrainte CHECK
    op.create_check_constraint(
        "check_t_individuals_nomenclature_sex",
        "t_individuals",
        "ref_nomenclatures.check_nomenclature_type_by_mnemonique(id_nomenclature_sex, 'SEXE'::character varying)",
        schema=SCHEMA_NAME,
    )

    # Insérer les nouvelles données
    op.execute(
        sa.insert(t_indiv).values(
            [
                {
                    "id_individual": 3,
                    "name": "Arture",
                    "cd_nom": 2852,
                    "id_nomenclature_sex": 164,
                    "additional_data": {"collier": "rouge", "taille_cm": 45},
                },
                {
                    "id_individual": 4,
                    "name": "Crâne d'oeuf",
                    "cd_nom": 2962,
                    "id_nomenclature_sex": 165,
                    "additional_data": {"collier": "vert/rouge", "taille_cm": 40.2},
                },
            ]
        )
    )

def downgrade():
    op.drop_constraint(
        "ck_t_individuals_id_nomenclature_sex",
        "t_individuals",
        schema=SCHEMA_NAME,
    )
    op.drop_column(
        "t_individuals",
        "id_nomenclature_sex",
        schema=SCHEMA_NAME,
    )
    #pass
