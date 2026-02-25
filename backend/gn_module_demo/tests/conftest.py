import os
import pytest
from sqlalchemy import select

# Ensure RefGeo/Marshmallow use the GeoNature SQLAlchemy instance during test discovery.
os.environ.setdefault("FLASK_SQLALCHEMY_DB", "geonature.utils.env.db")
os.environ.setdefault("FLASK_MARSHMALLOW", "geonature.utils.env.ma")

import geonature  # noqa: F401
from geonature.tests.fixtures import *
from geonature.tests.fixtures import _session, app, _app, users
from geonature.tests.test_permissions import g_permissions
from geonature.utils.config import config as gn_config
from geonature.utils.env import db
from geonature.core.gn_commons.models import TModules
from geonature.core.gn_permissions.models import PermAction, PermObject, Permission
from pypnusershub.tests.utils import logged_user

from gn_module_demo import MODULE_CODE, MODULE_LABEL, MODULE_PICTO
from gn_module_demo.blueprint import blueprint as demo_blueprint
from gn_module_demo.models import BibIndividualTag, Individuals


@pytest.fixture
def client(app):
    if "demo.list_demos" not in app.view_functions:
        module_config = gn_config.get(MODULE_CODE, {})
        url_prefix = module_config.get("MODULE_API", "/demo")
        if not url_prefix.startswith("/"):
            url_prefix = f"/{url_prefix}"
        app.register_blueprint(demo_blueprint, url_prefix=url_prefix)
    return app.test_client()


@pytest.fixture
def admin_client(client, users):
    """Client authentifie en tant qu'admin pour simplifier les tests API."""
    with logged_user(client, users["admin_user"]):
        yield client


@pytest.fixture
def taxref_sample(app):
    """Retourne une entree Taxref existante, sinon skippe les tests dependants."""
    from apptax.taxonomie.models import Taxref

    taxref = db.session.scalar(select(Taxref).order_by(Taxref.cd_nom))
    if taxref is None:
        pytest.skip("Taxref est vide: tests necessitent au moins une entree Taxref.")
    return taxref


@pytest.fixture
def individual_payload(taxref_sample):
    return {
        "name_individual": "Individual Test",
        "cd_nom": taxref_sample.cd_nom,
        "additional_data": {"age": 3, "sex": "F"},
    }


@pytest.fixture
def individual_in_db(taxref_sample):
    individual = Individuals(
        name_individual="Individual DB",
        cd_nom=taxref_sample.cd_nom,
        additional_data={"age": 5, "sex": "M"},
    )
    with db.session.begin_nested():
        db.session.add(individual)
        db.session.flush()
        db.session.refresh(individual)
    return individual


@pytest.fixture
def individuals_batch(taxref_sample):
    individuals = [
        Individuals(
            name_individual="Batch 1",
            cd_nom=taxref_sample.cd_nom,
            additional_data={"age": 2, "sex": "F"},
        ),
        Individuals(
            name_individual="Batch 2",
            cd_nom=taxref_sample.cd_nom,
            additional_data={"age": 4, "sex": "M"},
        ),
        Individuals(
            name_individual="Batch 3",
            cd_nom=taxref_sample.cd_nom,
            additional_data={"age": 6, "sex": "F"},
        ),
    ]
    with db.session.begin_nested():
        db.session.add_all(individuals)
        db.session.flush()
    return individuals


@pytest.fixture
def individual_tags():
    tag_defs = [
        ("TEST_M2M_A", "Tag de test A"),
        ("TEST_M2M_B", "Tag de test B"),
    ]
    tags = []
    with db.session.begin_nested():
        for code_tag, label_tag in tag_defs:
            tag = db.session.scalar(select(BibIndividualTag).where(BibIndividualTag.code_tag == code_tag))
            if tag is None:
                tag = BibIndividualTag(code_tag=code_tag, label_tag=label_tag)
                db.session.add(tag)
                db.session.flush()
            tags.append(tag)
    return tags


@pytest.fixture(scope="session", autouse=True)
def ensure_demo_module(app, users):
    """Ensure the module record and baseline permissions exist for tests."""
    module = db.session.scalar(select(TModules).filter_by(module_code=MODULE_CODE))
    if module is None:
        with db.session.begin_nested():
            module = TModules(
                module_code=MODULE_CODE,
                module_label=MODULE_LABEL,
                module_path=MODULE_CODE.lower(),
                module_picto=MODULE_PICTO,
                active_frontend=True,
                active_backend=True,
                ng_module=MODULE_CODE.lower(),
            )
            db.session.add(module)
        module = db.session.scalar(select(TModules).filter_by(module_code=MODULE_CODE))

    actions = {
        code: db.session.scalar(select(PermAction).filter_by(code_action=code)) for code in "CRUDV"
    }
    object_all = db.session.scalar(select(PermObject).filter_by(code_object="ALL"))

    target_permissions = {
        "admin_user": {"actions": "CRUDV", "scope": None},
        "self_user": {"actions": "R", "scope": 1},
    }

    with db.session.begin_nested():
        for username, config in target_permissions.items():
            user = users.get(username)
            if user is None:
                continue
            for action_code in config["actions"]:
                action = actions.get(action_code)
                if action is None or object_all is None:
                    continue
                exists = db.session.scalar(
                    select(Permission).where(
                        Permission.id_role == user.id_role,
                        Permission.id_module == module.id_module,
                        Permission.id_action == action.id_action,
                        Permission.id_object == object_all.id_object,
                    )
                )
                if exists is None:
                    permission = Permission(
                        id_role=user.id_role,
                        id_module=module.id_module,
                        id_action=action.id_action,
                        id_object=object_all.id_object,
                        scope_value=config["scope"],
                    )
                    db.session.add(permission)

    return module
