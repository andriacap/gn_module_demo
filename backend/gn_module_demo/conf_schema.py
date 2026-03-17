"""
Spécification du schéma toml des paramètres de configurations
"""

from marshmallow import Schema, fields


class GnModuleSchemaConf(Schema):
    TEXT = fields.String(load_default="Bonjour")
    OBSERVERS_LIST_CODE = fields.String(load_default="observateurs_indiv")
