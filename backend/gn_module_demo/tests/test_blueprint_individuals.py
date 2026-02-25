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
