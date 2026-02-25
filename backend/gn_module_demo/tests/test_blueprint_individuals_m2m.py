import pytest
from flask import url_for

from geonature.utils.env import db
from gn_module_demo.models import Individuals


@pytest.mark.integration
def test_list_individual_tags_returns_referential(admin_client, individual_tags):
    response = admin_client.get(url_for("demo.list_individual_tags"))

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)
    ids = {item["id_tag"] for item in payload}
    for tag in individual_tags:
        assert tag.id_tag in ids


@pytest.mark.integration
def test_create_individual_form_m2m_requires_tag_ids(admin_client, individual_payload):
    payload = dict(individual_payload)

    response = admin_client.post(url_for("demo.create_individual_form_m2m"), json=payload)

    assert response.status_code == 400


@pytest.mark.integration
def test_create_individual_form_m2m_populates_association_table(
    admin_client, individual_payload, individual_tags
):
    payload = dict(individual_payload)
    payload["tag_ids"] = [individual_tags[0].id_tag, individual_tags[1].id_tag]

    response = admin_client.post(url_for("demo.create_individual_form_m2m"), json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert "tags" in data
    returned_tag_ids = {tag["id_tag"] for tag in data["tags"]}
    assert returned_tag_ids == set(payload["tag_ids"])

    created = db.session.get(Individuals, data["id_individual"])
    persisted_tag_ids = {tag.id_tag for tag in created.tags}
    assert persisted_tag_ids == set(payload["tag_ids"])


@pytest.mark.integration
def test_update_individual_form_m2m_replaces_tags(admin_client, individual_payload, individual_tags):
    create_payload = dict(individual_payload)
    create_payload["tag_ids"] = [individual_tags[0].id_tag]
    created_resp = admin_client.post(url_for("demo.create_individual_form_m2m"), json=create_payload)
    assert created_resp.status_code == 200
    created = created_resp.get_json()

    update_payload = dict(individual_payload)
    update_payload["name_individual"] = "Updated with M2M"
    update_payload["tag_ids"] = [individual_tags[1].id_tag]
    update_resp = admin_client.put(
        url_for("demo.update_individual_form_m2m", id_individual=created["id_individual"]),
        json=update_payload,
    )

    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["name_individual"] == "Updated with M2M"
    returned_tag_ids = {tag["id_tag"] for tag in updated["tags"]}
    assert returned_tag_ids == {individual_tags[1].id_tag}

    persisted = db.session.get(Individuals, created["id_individual"])
    persisted_tag_ids = {tag.id_tag for tag in persisted.tags}
    assert persisted_tag_ids == {individual_tags[1].id_tag}
