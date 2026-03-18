import pytest
from flask import url_for
from sqlalchemy import select, func

from geonature.utils.env import db
from gn_module_demo_pnv.models import Demo
from pypnusershub.tests.utils import logged_user


def test_list_demos_returns_list(client, users):
    with logged_user(client, users["admin_user"]):
        response = client.get(url_for("demo.list_demos"))

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)


def test_get_demo_not_found(client, users):
    with logged_user(client, users["admin_user"]):
        response = client.get(url_for("demo.demo", id_demo=-1))

    assert response.status_code == 404


def test_get_demo_returns_payload(client, users):
    demo = db.session.scalar(select(Demo).order_by(Demo.id_demo))
    if demo is None:
        next_id = db.session.scalar(select(func.coalesce(func.max(Demo.id_demo), 0))) + 1
        with db.session.begin_nested():
            demo = Demo(id_demo=next_id)
            db.session.add(demo)
            db.session.flush()
            db.session.refresh(demo)

    with logged_user(client, users["admin_user"]):
        response = client.get(url_for("demo.demo", id_demo=demo.id_demo))

    assert response.status_code == 200
    data = response.get_json()
    assert data["id_demo"] == demo.id_demo
