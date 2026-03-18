from geonature.utils.env import DB
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from apptax.taxonomie.models import Taxref

# from sqlalchemy.ext.hybrid import hybrid_property

from pypnnomenclature.models import TNomenclatures as Nomenclature
from pypnnomenclature.utils import NomenclaturesMixin

SCHEMA_NAME = "gn_demo_pnv"

class Demo(DB.Model):
    __tablename__ = "t_demos"
    __table_args__ = {"schema": SCHEMA_NAME}

    id_demo = DB.Column(
        "id_demo",
        DB.Integer,
        primary_key=True,
        autoincrement=True,
    )

class Individual(NomenclaturesMixin, DB.Model):
    __tablename__ = "t_individuals"
    __table_args__ = {"schema": SCHEMA_NAME}

    id_individual = DB.Column(
        "id_individual",
        DB.Integer,
        primary_key=True,
        autoincrement=True,
    )

    name = DB.Column(
        "name",
        DB.Text,
        nullable=True,
    )

    id_nomenclature_sex = DB.Column(
        DB.Integer, 
        DB.ForeignKey(Nomenclature.id_nomenclature)
    )

    nomenclature_sex = DB.relationship(
        Nomenclature,
        foreign_keys=[id_nomenclature_sex]
    )

    cd_nom = DB.Column("cd_nom", DB.Integer, DB.ForeignKey(Taxref.cd_nom))

    additional_data = DB.Column(
        "additional_data",
        JSONB,
        nullable=True,
        # Permet de faire générer pour alembic une valeur par défaut
        server_default="{}",
    )

    taxref = DB.relationship(
        Taxref,
        lazy="joined",
        viewonly=True,
    )

    geom_local = DB.Column(
        Geometry("GEOMETRY", 4326, nullable=True)
    )
