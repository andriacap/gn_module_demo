import pytest
from geoalchemy2.shape import to_shape
from marshmallow import ValidationError

from gn_module_demo.schema import IndividualsSchema

pytestmark = pytest.mark.usefixtures("app")


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"additional_data": {"age": 2}},
        {"additional_data": {"sex": "F"}},
        {"additional_data": "not-a-dict"},
    ],
    ids=["missing-sex", "missing-age", "wrong-type"],
)
def test_individuals_schema_rejects_invalid_additional_data(payload):
    schema = IndividualsSchema()

    with pytest.raises(ValidationError) as excinfo:
        schema.load(payload)

    assert "additional_data" in excinfo.value.messages


@pytest.mark.unit
def test_individuals_schema_accepts_valid_additional_data(individual_payload):
    schema = IndividualsSchema()

    individual = schema.load(individual_payload)

    assert individual.additional_data["age"] == 3
    assert individual.additional_data["sex"] == "F"


@pytest.mark.unit
def test_individuals_schema_accepts_valid_geom(individual_payload):
    schema = IndividualsSchema(as_geojson=True)
    payload = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [6.375, 45.501],
        },
        "properties": dict(individual_payload),
    }

    individual = schema.load(payload)
    geom = to_shape(individual.geom)
    dumped = schema.dump(individual)

    assert geom.geom_type == "Point"
    assert dumped["geometry"]["type"] == "Point"


@pytest.mark.unit
def test_individuals_schema_rejects_invalid_geom_type(individual_payload):
    schema = IndividualsSchema(as_geojson=True)
    payload = {
        "type": "Feature",
        "geometry": {
            "type": "MultiPoint",
            "coordinates": [[6.3, 45.5], [6.4, 45.6]],
        },
        "properties": dict(individual_payload),
    }

    with pytest.raises(ValidationError) as excinfo:
        schema.load(payload)

    assert "geom" in excinfo.value.messages


@pytest.mark.unit
def test_individuals_schema_smart_relationships_can_include_taxref(individual_in_db):
    schema = IndividualsSchema(only=["taxref"])

    dumped = schema.dump(individual_in_db)

    assert "id_individual" in dumped
    assert "name_individual" in dumped
    assert "taxref" in dumped


@pytest.mark.xfail(reason="Le validateur exige age + sex, pas 'au moins un'.")
def test_individuals_schema_accepts_one_field_only():
    schema = IndividualsSchema()

    individual = schema.load({"additional_data": {"age": 1}})

    assert individual.additional_data["age"] == 1
