"""init model

Revision ID: 943bedffa102
Revises:
Create Date: 2023-03-27 11:54:34.602380

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "943bedffa102"
down_revision = None
branch_labels = ("demo",)
depends_on = None

MODULE_CODE = "DEMO"
SCHEMA_NAME = "gn_demo"
TABLE_NAME = "t_demos"
PRIMARY_KEY = "id_demo"

NOTIFICATION_SCHEMA = "gn_notifications"
NOTIFICATION_CATEGORY_DEFINITIONS = [
    {
        "code": "PERMISSION_REQUEST_VIEW",
        "label": "Lecture d'une demande",
        "description": "Lecture d'une demande de permission",
        "action_code": "R",
    },
]


def upgrade():
    # #########################################################################
    # Schema pr_demo
    # #########################################################################
    conn = op.get_bind()
    op.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}"))

    op.create_table(
        TABLE_NAME,
        sa.Column(
            PRIMARY_KEY,
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        schema=SCHEMA_NAME,
    )

    ## ########################################################################
    ## Module permissions
    ## ########################################################################
    op.execute(
        f"""
      INSERT INTO
          gn_permissions.t_permissions_available (
              id_module,
              id_object,
              id_action,
              label,
              scope_filter
          )
      SELECT
          m.id_module,
          o.id_object,
          a.id_action,
          v.label,
          v.scope_filter
      FROM
          (
              VALUES
                  ('{MODULE_CODE}', 'ALL', 'C', False, 'Créer des demo')
                  ,('{MODULE_CODE}', 'ALL', 'R', True, 'Voir des demos')
                  ,('{MODULE_CODE}', 'ALL', 'U', True, 'Modifier des demos')
                  ,('{MODULE_CODE}', 'ALL', 'V', True, 'Valider des demos')
                  ,('{MODULE_CODE}', 'ALL', 'D', True, 'Supprimer des demos')
          ) AS v (module_code, object_code, action_code, scope_filter, label)
      JOIN
          gn_commons.t_modules m ON m.module_code = v.module_code
      JOIN
          gn_permissions.t_objects o ON o.code_object = v.object_code
      JOIN
          gn_permissions.bib_actions a ON a.code_action = v.action_code
      """
    )


def downgrade():
    conn = op.get_bind()
    module_id = conn.execute(
        sa.text(
            """
            SELECT id_module
            FROM gn_commons.t_modules
            WHERE module_code = :module_code
            """
        ),
        {"module_code": MODULE_CODE},
    ).scalar()

    conn.execute(
        sa.text(
            """
            DELETE FROM gn_permissions.t_permissions_available
            WHERE id_module = :module_id
            """
        ),
        {"module_id": module_id},
    )

    # #########################################################################
    # Schema pr_demo
    # #########################################################################
    op.drop_table(TABLE_NAME, schema=SCHEMA_NAME)
    op.execute(sa.text(f"DROP SCHEMA IF EXISTS {SCHEMA_NAME} CASCADE"))
