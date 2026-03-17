import pytest
from flask import url_for
from geoalchemy2.shape import to_shape

from geonature.utils.env import db
from gn_module_demo.models import Individuals
from gn_module_demo import blueprint as demo_blueprint_module


@pytest.mark.integration
@pytest.mark.parametrize(
    "endpoint",
    [
        "demo.list_individuals",
        "demo.list_individuals_manual",
        "demo.list_individuals_schema",
    ],
)
def test_list_individuals_endpoints_return_list(admin_client, individuals_batch, endpoint):
    response = admin_client.get(url_for(endpoint))

    assert response.status_code == 200
    payload = response.get_json()
    if endpoint == "demo.list_individuals":
        assert isinstance(payload, dict)
        assert isinstance(payload.get("items"), list)
        assert payload.get("page") is not None
        assert payload.get("per_page") is not None
        assert payload.get("pages") is not None
        assert payload.get("total") is not None
        if payload["items"]:
            assert "taxref" in payload["items"][0]
    else:
        assert isinstance(payload, list)


@pytest.mark.integration
def test_list_individuals_geojson_returns_feature_collection(admin_client, individuals_batch):
    response = admin_client.get(url_for("demo.list_individuals_geojson"))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["type"] == "FeatureCollection"
    assert isinstance(payload["features"], list)
    if payload["features"]:
        feature = payload["features"][0]
        assert feature["type"] == "Feature"
        assert "id" in feature
        assert "properties" in feature
        assert "id_individual" in feature["properties"]


@pytest.mark.integration
def test_individual_filters_are_consistent_between_list_and_map(admin_client, individual_payload, users):
    observer_a_id = users["admin_user"].id_role
    observer_b_id = users["self_user"].id_role

    payload_a = dict(individual_payload)
    payload_a["name_individual"] = "Filter API A"
    payload_a["observer"] = observer_a_id
    payload_a["additional_data"] = {
        "age": 2,
        "sex": "F",
        "observation_date": "2026-02-10",
    }

    payload_b = dict(individual_payload)
    payload_b["name_individual"] = "Filter API B"
    payload_b["observer"] = observer_b_id
    payload_b["additional_data"] = {
        "age": 4,
        "sex": "M",
        "observation_date": "2025-01-05",
    }

    create_response_a = admin_client.post(url_for("demo.create_individual"), json=payload_a)
    create_response_b = admin_client.post(url_for("demo.create_individual"), json=payload_b)
    assert create_response_a.status_code == 200
    assert create_response_b.status_code == 200
    created_a = create_response_a.get_json()
    created_b = create_response_b.get_json()

    filters = {
        "observer": str(observer_a_id),
        "date_from": "2026-01-01",
        "date_to": "2026-12-31",
        "limit": 500,
    }
    list_response = admin_client.get(url_for("demo.list_individuals"), query_string=filters)
    map_response = admin_client.get(url_for("demo.list_individuals_geojson"), query_string=filters)

    assert list_response.status_code == 200
    assert map_response.status_code == 200

    list_payload = list_response.get_json()
    map_payload = map_response.get_json()

    list_ids = {item["id_individual"] for item in list_payload["items"]}
    map_ids = {feature["properties"]["id_individual"] for feature in map_payload["features"]}

    matching_list_item = next(
        (item for item in list_payload["items"] if item["id_individual"] == created_a["id_individual"]),
        None,
    )
    expected_observer_name = " ".join(
        part for part in [users["admin_user"].nom_role, users["admin_user"].prenom_role] if part
    ).strip() or (users["admin_user"].nom_complet or "").strip()

    assert created_a["id_individual"] in list_ids
    assert created_a["id_individual"] in map_ids
    assert created_b["id_individual"] not in list_ids
    assert created_b["id_individual"] not in map_ids
    assert matching_list_item is not None
    assert matching_list_item["observer_full_name"] == expected_observer_name


@pytest.mark.integration
def test_list_individuals_rejects_invalid_date_filter(admin_client):
    response = admin_client.get(
        url_for("demo.list_individuals"),
        query_string={"date_from": "2026-99-01"},
    )

    assert response.status_code == 400


@pytest.mark.integration
def test_create_individual_requires_json(admin_client):
    response = admin_client.post(url_for("demo.create_individual"))

    assert response.status_code == 400


@pytest.mark.integration
def test_create_individual_rejects_id_in_payload(admin_client, individual_payload):
    payload = dict(individual_payload)
    payload["id_individual"] = 1234

    response = admin_client.post(url_for("demo.create_individual"), json=payload)

    assert response.status_code == 400


@pytest.mark.integration
def test_create_update_delete_individual_flow(admin_client, individual_payload):
    response = admin_client.post(url_for("demo.create_individual"), json=individual_payload)

    assert response.status_code == 200
    created = response.get_json()
    individual_id = created["id_individual"]

    response = admin_client.put(
        url_for("demo.update_individual", id_individual=individual_id),
        json={"name_individual": "Updated via API"},
    )
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["name_individual"] == "Updated via API"

    response = admin_client.delete(url_for("demo.delete_individual", id_individual=individual_id))
    assert response.status_code == 200
    assert db.session.get(Individuals, individual_id) is None


@pytest.mark.integration
def test_create_individual_with_geom(admin_client, individual_payload):
    payload = dict(individual_payload)
    payload["geom"] = {"type": "Point", "coordinates": [6.375, 45.501]}

    response = admin_client.post(url_for("demo.create_individual"), json=payload)

    assert response.status_code == 200
    created = response.get_json()
    assert created["geom"]["type"] == "Point"

    created_in_db = db.session.get(Individuals, created["id_individual"])
    assert to_shape(created_in_db.geom).geom_type == "Point"


@pytest.mark.integration
def test_update_individual_not_found(admin_client):
    response = admin_client.put(
        url_for("demo.update_individual", id_individual=-9999),
        json={"name_individual": "Does not matter"},
    )

    assert response.status_code == 404


@pytest.mark.integration
def test_delete_individual_not_found(admin_client):
    response = admin_client.delete(url_for("demo.delete_individual", id_individual=-9999))

    assert response.status_code == 404


@pytest.mark.integration
def test_list_individuals_manual_uses_repository(monkeypatch, admin_client):
    class DummyTaxref:
        cd_nom = 321
        nom_complet = "Dummy taxref"

    class DummyIndividual:
        id_individual = 99
        name_individual = "Dummy"
        cd_nom = 321
        geom = None
        taxref = DummyTaxref()

    monkeypatch.setattr(
        demo_blueprint_module,
        "repo_list_individuals_with_taxref",
        lambda load_strategy="joined": [DummyIndividual()],
    )

    response = admin_client.get(url_for("demo.list_individuals_manual"))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]["taxref"]["cd_nom"] == 321
