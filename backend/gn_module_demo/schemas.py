from geonature.utils.env import db, ma
from utils_flask_sqla_geo.schema import GeoAlchemyAutoSchema,GeoModelConverter
from apptax.taxonomie.schemas import TaxrefSchema
from utils_flask_sqla.schema import SmartRelationshipsMixin
from marshmallow import fields, validates, ValidationError
from apptax.taxonomie.models import Taxref

from .models import Individual

from pypnnomenclature.utils import NomenclaturesConverter

ADDITIONAL_DATA_ALLOWED_KEYS = ["collier", "taille_cm"]

class IndividualConverter(NomenclaturesConverter, GeoModelConverter):
    pass

class IndividualSchema(SmartRelationshipsMixin, GeoAlchemyAutoSchema):
    class Meta:
        model = Individual
        include_fk = True
        load_instance = True
        sqla_session = db.session
        # A initialiser seulement si plus d'un converteur, sinon avec GeoAlchemy cette variableest initialisée avec GeoConverter
        model_converter = IndividualConverter
        feature_id = "id_individual"  # optionnel, pour associer un id à la géométrie
        feature_geometry = "geom_local"  # automatiquement déterminé

    id_individual = ma.auto_field(dump_only=True)
    taxref = ma.Nested(TaxrefSchema)


    @validates("additional_data")
    # create an instance method that takes a value for additional_data
    def validates_additional_data(self, additional_data):

        if additional_data is not None and not isinstance(additional_data, dict):
            raise ValidationError("additional_data must be a JSON object (dict).")

        if not all(field in additional_data.keys() for field in ADDITIONAL_DATA_ALLOWED_KEYS):
            raise ValidationError(
                f"additional_data must contains these fields: {ADDITIONAL_DATA_ALLOWED_KEYS}."
            )

        # Tester si le cd_nom de additionnal_data existe dans Taxref
        cd_nom_payload = additional_data.get("cd_nom")
        if cd_nom_payload is not None:
            cd_nom_additional = db.session.execute(
                db.select(Taxref).filter_by(cd_nom=cd_nom_payload)
            ).scalars().one_or_none()

            if cd_nom_additional is None:
                raise ValidationError(
                    f"cd_nom {cd_nom_payload} in additional_data does not exist in taxref."
                )
            return additional_data