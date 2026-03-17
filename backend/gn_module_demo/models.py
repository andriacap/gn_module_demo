from geoalchemy2 import Geometry
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from apptax.taxonomie.models import Taxref
from geonature.utils.env import DB
from pypnusershub.db.models import User


class Demo(DB.Model):
    __tablename__ = "t_demos"
    __table_args__ = {"schema": "gn_demo"}

    id_demo = DB.Column(
        "id_demo",
        DB.Integer,
        primary_key=True,
        autoincrement=True,
    )


cor_individual_tag = DB.Table(
    "cor_individual_tag",
    DB.Column(
        "id_individual",
        DB.Integer,
        DB.ForeignKey("gn_demo.t_individuals.id_individual", ondelete="CASCADE"),
        primary_key=True,
    ),
    DB.Column(
        "id_tag",
        DB.Integer,
        DB.ForeignKey("gn_demo.bib_individual_tags.id_tag", ondelete="CASCADE"),
        primary_key=True,
    ),
    schema="gn_demo",
)


class BibIndividualTag(DB.Model):
    __tablename__ = "bib_individual_tags"
    __table_args__ = (
        UniqueConstraint("code_tag", name="uq_gn_demo_bib_individual_tags_code_tag"),
        {"schema": "gn_demo"},
    )

    id_tag = DB.Column(
        "id_tag",
        DB.Integer,
        primary_key=True,
        autoincrement=True,
    )
    code_tag = DB.Column("code_tag", DB.String(50), nullable=False)
    label_tag = DB.Column("label_tag", DB.String(255), nullable=False)


class Individuals(DB.Model):
    __tablename__ = "t_individuals"
    __table_args__ = {"schema": "gn_demo"}

    id_individual = DB.Column(
        "id_individual",
        DB.Integer,
        primary_key=True,
        autoincrement=True,
    )

    name_individual = DB.Column(
        "name_individual",
        DB.String(255),
    )

    cd_nom = DB.Column(
        "cd_nom",
        DB.Integer,
        DB.ForeignKey(Taxref.cd_nom),
    )

    observer = DB.Column(
        "observer",
        DB.Integer,
        DB.ForeignKey(User.id_role),
        nullable=True,
    )

    geom = DB.Column(
        "geom",
        Geometry("GEOMETRY", 4326),
        nullable=True,
    )

    additional_data = DB.Column(
        "additional_data",
        JSONB,
        nullable=True,
        server_default="{}",
    )

    taxref = DB.relationship(
        Taxref,
        foreign_keys=[cd_nom],
        lazy="select",
    )

    tags = DB.relationship(
        BibIndividualTag,
        secondary=cor_individual_tag,
        lazy="selectin",
        backref=DB.backref("individuals", lazy="selectin"),
    )

    observer_role = DB.relationship(
        User,
        foreign_keys=[observer],
        lazy="select",
    )
