"""add observer column and seed 100 sample individuals

Revision ID: d7a1c2f4b9e0
Revises: c9e4b7a1d2f0
Create Date: 2026-03-04 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d7a1c2f4b9e0"
down_revision = "c9e4b7a1d2f0"
branch_labels = None
depends_on = None

SCHEMA_NAME = "gn_demo"
TABLE_NAME = "t_individuals"
COLUMN_NAME = "observer"
SAMPLE_NAME_PREFIX = "Sample Individu"
USERS_SCHEMA = "utilisateurs"
USERS_TABLE = "t_roles"
USERS_LIST_TABLE = "t_listes"
USERS_LIST_LINK_TABLE = "cor_role_liste"
FK_NAME = "fk_gn_demo_t_individuals_observer_t_roles"
DEMO_OBSERVER_REMARKS = "Demo observer for gn_module_demo sample individuals"
DEMO_OBSERVER_LIST_CODE = "observateurs_individ"
DEMO_OBSERVER_LIST_NAME = "observateurs_individus"
DEMO_OBSERVER_LIST_DESCRIPTION = "Liste des observateurs du module gn_module_demo"
DEMO_OBSERVERS = (
    ("demo.observer.001", "DemoObserver", "Alpha", "demo.observer.001@example.local"),
    ("demo.observer.002", "DemoObserver", "Beta", "demo.observer.002@example.local"),
    ("demo.observer.003", "DemoObserver", "Gamma", "demo.observer.003@example.local"),
    ("demo.observer.004", "DemoObserver", "Delta", "demo.observer.004@example.local"),
    ("demo.observer.005", "DemoObserver", "Epsilon", "demo.observer.005@example.local"),
)
DEMO_OBSERVER_IDENTIFIERS_SQL = ", ".join(f"'{row[0]}'" for row in DEMO_OBSERVERS)
DEMO_OBSERVERS_VALUES_SQL = ",\n                    ".join(
    f"('{identifiant}', '{nom_role}', '{prenom_role}', '{email}')"
    for identifiant, nom_role, prenom_role, email in DEMO_OBSERVERS
)


def upgrade():
    op.add_column(
        TABLE_NAME,
        sa.Column(COLUMN_NAME, sa.Integer(), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.create_foreign_key(
        FK_NAME,
        TABLE_NAME,
        USERS_TABLE,
        [COLUMN_NAME],
        ["id_role"],
        source_schema=SCHEMA_NAME,
        referent_schema=USERS_SCHEMA,
        ondelete="SET NULL",
    )

    op.execute(
        sa.text(
            f"""
            WITH source (identifiant, nom_role, prenom_role, email) AS (
                VALUES
                    {DEMO_OBSERVERS_VALUES_SQL}
            )
            INSERT INTO {USERS_SCHEMA}.{USERS_TABLE} (
                groupe,
                identifiant,
                nom_role,
                prenom_role,
                email,
                active,
                remarques
            )
            SELECT
                FALSE,
                s.identifiant,
                s.nom_role,
                s.prenom_role,
                s.email,
                TRUE,
                '{DEMO_OBSERVER_REMARKS}'
            FROM source s
            WHERE NOT EXISTS (
                SELECT 1
                FROM {USERS_SCHEMA}.{USERS_TABLE} u
                WHERE u.identifiant = s.identifiant
            )
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            INSERT INTO {USERS_SCHEMA}.{USERS_LIST_TABLE} (
                code_liste,
                nom_liste,
                desc_liste
            )
            SELECT
                '{DEMO_OBSERVER_LIST_CODE}',
                '{DEMO_OBSERVER_LIST_NAME}',
                '{DEMO_OBSERVER_LIST_DESCRIPTION}'
            WHERE NOT EXISTS (
                SELECT 1
                FROM {USERS_SCHEMA}.{USERS_LIST_TABLE} l
                WHERE l.code_liste = '{DEMO_OBSERVER_LIST_CODE}'
            )
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            WITH observer_list AS (
                SELECT l.id_liste
                FROM {USERS_SCHEMA}.{USERS_LIST_TABLE} l
                WHERE l.code_liste = '{DEMO_OBSERVER_LIST_CODE}'
                LIMIT 1
            ),
            demo_observers AS (
                SELECT u.id_role
                FROM {USERS_SCHEMA}.{USERS_TABLE} u
                WHERE u.identifiant IN ({DEMO_OBSERVER_IDENTIFIERS_SQL})
            )
            INSERT INTO {USERS_SCHEMA}.{USERS_LIST_LINK_TABLE} (
                id_role,
                id_liste
            )
            SELECT
                o.id_role,
                l.id_liste
            FROM demo_observers o
            CROSS JOIN observer_list l
            WHERE NOT EXISTS (
                SELECT 1
                FROM {USERS_SCHEMA}.{USERS_LIST_LINK_TABLE} c
                WHERE c.id_role = o.id_role
                    AND c.id_liste = l.id_liste
            )
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            WITH raw_observer AS (
                SELECT
                    i.id_individual,
                    NULLIF(
                        BTRIM(
                            COALESCE(
                                i.additional_data ->> 'observer',
                                i.additional_data ->> 'author',
                                i.additional_data ->> 'auteur'
                            )
                        ),
                        ''
                    ) AS observer_text
                FROM {SCHEMA_NAME}.{TABLE_NAME} i
                WHERE i.observer IS NULL
            ),
            matched_observer AS (
                SELECT
                    r.id_individual,
                    u.id_role,
                    ROW_NUMBER() OVER (PARTITION BY r.id_individual ORDER BY u.id_role ASC) AS rn
                FROM raw_observer r
                JOIN {USERS_SCHEMA}.{USERS_TABLE} u
                    ON r.observer_text IS NOT NULL
                    AND (
                        LOWER(u.identifiant) = LOWER(r.observer_text)
                        OR LOWER(CONCAT_WS(' ', u.nom_role, u.prenom_role)) = LOWER(r.observer_text)
                        OR LOWER(CONCAT_WS(' ', u.prenom_role, u.nom_role)) = LOWER(r.observer_text)
                    )
            )
            UPDATE {SCHEMA_NAME}.{TABLE_NAME} i
            SET observer = m.id_role
            FROM matched_observer m
            WHERE i.id_individual = m.id_individual
                AND m.rn = 1
                AND i.observer IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            WITH demo_observers AS (
                SELECT
                    u.id_role,
                    u.nom_role,
                    u.prenom_role,
                    ROW_NUMBER() OVER (ORDER BY u.identifiant ASC) AS rn
                FROM {USERS_SCHEMA}.{USERS_TABLE} u
                WHERE u.identifiant IN ({DEMO_OBSERVER_IDENTIFIERS_SQL})
            ),
            observer_count AS (
                SELECT COUNT(*) AS total
                FROM demo_observers
            ),
            first_taxref AS (
                SELECT t.cd_nom
                FROM taxonomie.taxref t
                ORDER BY t.cd_nom
                LIMIT 1
            ),
            vanoise_area AS (
                SELECT COALESCE(
                    (
                        SELECT la.geom_4326
                        FROM ref_geo.l_areas la
                        WHERE la.geom_4326 IS NOT NULL
                            AND LOWER(la.area_name) LIKE '%parc national de la vanoise%'
                        ORDER BY ST_Area(la.geom_4326::geography) DESC
                        LIMIT 1
                    ),
                    (
                        SELECT la.geom_4326
                        FROM ref_geo.l_areas la
                        WHERE la.geom_4326 IS NOT NULL
                            AND LOWER(la.area_name) LIKE '%vanoise%'
                        ORDER BY ST_Area(la.geom_4326::geography) DESC
                        LIMIT 1
                    ),
                    ST_GeomFromText(
                        'POLYGON((6.75 45.20, 7.20 45.20, 7.20 45.60, 6.75 45.60, 6.75 45.20))',
                        4326
                    )
                ) AS geom_4326
            ),
            generated_points AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY (SELECT 1)) AS idx,
                    (dumped.geom)::geometry(POINT, 4326) AS geom
                FROM vanoise_area va
                CROSS JOIN LATERAL ST_Dump(ST_GeneratePoints(va.geom_4326, 100)) dumped
            ),
            generated AS (
                SELECT
                    gs AS idx,
                    '{SAMPLE_NAME_PREFIX} ' || LPAD(gs::text, 3, '0') AS name_individual,
                    CASE
                        WHEN gs % 3 = 1 THEN 'F'
                        WHEN gs % 3 = 2 THEN 'M'
                        ELSE 'U'
                    END AS sex,
                    (DATE '2026-01-01' + ((gs - 1) % 365))::text AS observation_date
                FROM generate_series(1, 100) AS gs
            )
            INSERT INTO {SCHEMA_NAME}.{TABLE_NAME} (
                name_individual,
                cd_nom,
                observer,
                geom,
                additional_data
            )
            SELECT
                g.name_individual,
                first_taxref.cd_nom,
                o.id_role,
                gp.geom,
                jsonb_build_object(
                    'age', 1 + (g.idx % 12),
                    'sex', g.sex,
                    'observer', CONCAT_WS(' ', o.nom_role, o.prenom_role),
                    'observer_id', o.id_role,
                    'observation_date', g.observation_date
                )
            FROM generated g
            CROSS JOIN first_taxref
            JOIN observer_count oc
                ON oc.total > 0
            JOIN demo_observers o
                ON o.rn = ((g.idx - 1) % oc.total) + 1
            JOIN generated_points gp
                ON gp.idx = g.idx
            """
        )
    )


def downgrade():
    op.execute(
        sa.text(
            f"""
            DELETE FROM {SCHEMA_NAME}.{TABLE_NAME}
            WHERE name_individual LIKE '{SAMPLE_NAME_PREFIX} %'
            """
        )
    )
    op.drop_constraint(FK_NAME, TABLE_NAME, schema=SCHEMA_NAME, type_="foreignkey")
    op.drop_column(TABLE_NAME, COLUMN_NAME, schema=SCHEMA_NAME)

    op.execute(
        sa.text(
            f"""
            DELETE FROM {USERS_SCHEMA}.{USERS_LIST_LINK_TABLE} c
            USING {USERS_SCHEMA}.{USERS_TABLE} u, {USERS_SCHEMA}.{USERS_LIST_TABLE} l
            WHERE c.id_role = u.id_role
                AND c.id_liste = l.id_liste
                AND u.identifiant IN ({DEMO_OBSERVER_IDENTIFIERS_SQL})
                AND l.code_liste = '{DEMO_OBSERVER_LIST_CODE}'
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            DELETE FROM {USERS_SCHEMA}.{USERS_LIST_TABLE} l
            WHERE l.code_liste = '{DEMO_OBSERVER_LIST_CODE}'
                AND l.desc_liste = '{DEMO_OBSERVER_LIST_DESCRIPTION}'
                AND NOT EXISTS (
                    SELECT 1
                    FROM {USERS_SCHEMA}.{USERS_LIST_LINK_TABLE} c
                    WHERE c.id_liste = l.id_liste
                )
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            DELETE FROM {USERS_SCHEMA}.{USERS_TABLE}
            WHERE identifiant IN ({DEMO_OBSERVER_IDENTIFIERS_SQL})
                AND remarques = '{DEMO_OBSERVER_REMARKS}'
            """
        )
    )
