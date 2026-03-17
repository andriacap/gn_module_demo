"""
Définition des routes du module export
"""

import csv
import os
from contextlib import contextmanager
from datetime import date
from io import StringIO
from urllib.parse import urlparse

from flask import Blueprint, Response, current_app, jsonify, render_template, request, url_for
from marshmallow import ValidationError
from geoalchemy2.shape import to_shape
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, event, select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import (
    Session,
    defer,
    joinedload,
    load_only,
    noload,
    registry,
    relationship,
    selectinload,
)
from werkzeug.exceptions import BadRequest, NotFound

from geonature.core.gn_permissions import decorators as permissions
from geonature.core.gn_permissions.decorators import login_required
from geonature.utils.env import db
from utils_flask_sqla.response import json_resp

from . import MODULE_CODE
from .models import Demo, Individuals
from .repositories import (
    compute_demo_stats as repo_compute_demo_stats,
    count_individuals_by_taxref as repo_count_individuals_by_taxref,
    create_individual as repo_create_individual,
    delete_individual as repo_delete_individual,
    get_individual_tags_by_ids as repo_get_individual_tags_by_ids,
    get_individual_with_taxref_and_tags as repo_get_individual_with_taxref_and_tags,
    list_individuals_csv_rows as repo_list_individuals_csv_rows,
    list_individual_tags as repo_list_individual_tags,
    paginate_individuals_with_taxref as repo_paginate_individuals_with_taxref,
    list_individuals_for_map as repo_list_individuals_for_map,
    list_individuals_projection as repo_list_individuals_projection,
    list_individuals_with_taxref as repo_list_individuals_with_taxref,
    repo_raise_for_demo as repo_raise_for_demo,
    save_individual_with_tags as repo_save_individual_with_tags,
    search_taxref_autocomplete as repo_search_taxref_autocomplete,
    update_individual as repo_update_individual,
)
from .schema import (
    demo_list_schema,
    demo_schema,
    individual_form_m2m_schema,
    individual_tag_list_schema,
    IndividualsSchema,
    taxref_autocomplete_schema,
)

blueprint = Blueprint("demo", __name__, cli_group="demo")
blueprint.template_folder = os.path.join(blueprint.root_path, "templates")


@contextmanager
def _sql_debug(label):
    # Scope SQL debug listener to the current connection to avoid mutating
    # the global engine listeners while concurrent requests are running.
    connection = db.session.connection()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        print(f"[sql:{label}] {statement} | params={parameters}")

    event.listen(connection, "before_cursor_execute", before_cursor_execute)
    try:
        yield
    finally:
        if event.contains(connection, "before_cursor_execute", before_cursor_execute):
            event.remove(connection, "before_cursor_execute", before_cursor_execute)


def _serialize_individuals_manual(individuals):
    results = []
    for ind in individuals:
        taxref = None
        if ind.taxref:
            taxref = {
                "cd_nom": ind.taxref.cd_nom,
                "nom_complet": ind.taxref.nom_complet,
            }
        geom = to_shape(ind.geom).__geo_interface__ if ind.geom else None
        results.append(
            {
                "id_individual": ind.id_individual,
                "name_individual": ind.name_individual,
                "cd_nom": ind.cd_nom,
                "geom": geom,
                "taxref": taxref,
            }
        )
    return results


def _individual_payload_to_feature(payload):
    payload = dict(payload or {})
    geometry = payload.pop("geom", None)
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": payload,
    }


def _feature_to_individual_payload(feature):
    if not isinstance(feature, dict):
        return feature
    properties = dict(feature.get("properties") or {})
    properties["geom"] = feature.get("geometry")
    return properties


def _load_individual_form_m2m_payload():
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequest("JSON body is required")
    try:
        return individual_form_m2m_schema.load(payload)
    except ValidationError as exc:
        raise BadRequest(exc.messages) from exc


def _load_individual_filters():
    name = (request.args.get("name", type=str) or "").strip()
    taxref_query = (request.args.get("taxref", type=str) or "").strip()
    observer = (request.args.get("observer", type=str) or "").strip()
    date_from = (request.args.get("date_from", type=str) or "").strip()
    date_to = (request.args.get("date_to", type=str) or "").strip()

    try:
        date_from_value = date.fromisoformat(date_from) if date_from else None
    except ValueError as exc:
        raise BadRequest("date_from must use ISO format YYYY-MM-DD") from exc

    try:
        date_to_value = date.fromisoformat(date_to) if date_to else None
    except ValueError as exc:
        raise BadRequest("date_to must use ISO format YYYY-MM-DD") from exc

    if date_from_value and date_to_value and date_from_value > date_to_value:
        raise BadRequest("date_from must be less than or equal to date_to")

    return {
        "name": name or None,
        "taxref_query": taxref_query or None,
        "observer": observer or None,
        "date_from": date_from_value.isoformat() if date_from_value else None,
        "date_to": date_to_value.isoformat() if date_to_value else None,
    }


def _build_backref_demo():
    mapper_registry = registry()
    Base = mapper_registry.generate_base()

    class Parent(Base):
        __tablename__ = "demo_parent_backref"
        id_parent = Column(Integer, primary_key=True)
        name = Column(String(50))
        children = relationship("Child", backref="parent")

    class Child(Base):
        __tablename__ = "demo_child_backref"
        id_child = Column(Integer, primary_key=True)
        name = Column(String(50))
        id_parent = Column(Integer, ForeignKey("demo_parent_backref.id_parent"))

    parent = Parent(id_parent=1, name="Parent A")
    child = Child(id_child=10, name="Child 1")
    parent.children.append(child)

    print("backref parent.children count:", len(parent.children))
    print("backref child.parent.name:", child.parent.name)

    return parent, child


def _build_back_populates_demo():
    mapper_registry = registry()
    Base = mapper_registry.generate_base()

    class Parent(Base):
        __tablename__ = "demo_parent_back_populates"
        id_parent = Column(Integer, primary_key=True)
        name = Column(String(50))
        children = relationship("Child", back_populates="parent")

    class Child(Base):
        __tablename__ = "demo_child_back_populates"
        id_child = Column(Integer, primary_key=True)
        name = Column(String(50))
        id_parent = Column(Integer, ForeignKey("demo_parent_back_populates.id_parent"))
        parent = relationship("Parent", back_populates="children")

    parent = Parent(id_parent=1, name="Parent B")
    child = Child(id_child=20, name="Child 2")
    child.parent = parent

    print("back_populates parent.children count:", len(parent.children))
    print("back_populates child.parent.name:", child.parent.name)

    return parent, child


def _build_inmemory_joinedload_demo():
    mapper_registry = registry()
    Base = mapper_registry.generate_base()

    class Parent(Base):
        __tablename__ = "demo_parent_joinedload"
        id_parent = Column(Integer, primary_key=True)
        name = Column(String(50))
        children = relationship("Child", back_populates="parent")

    class Child(Base):
        __tablename__ = "demo_child_joinedload"
        id_child = Column(Integer, primary_key=True)
        name = Column(String(50))
        id_parent = Column(Integer, ForeignKey("demo_parent_joinedload.id_parent"))
        parent = relationship("Parent", back_populates="children")

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        parent = Parent(id_parent=1, name="Parent A")
        parent.children = [
            Child(id_child=10, name="Child 1"),
            Child(id_child=11, name="Child 2"),
        ]
        session.add(parent)
        session.commit()

        query = select(Parent).options(joinedload(Parent.children))
        try:
            parents_raw = session.scalars(query).all()
            raw_ids = [p.id_parent for p in parents_raw]
        except InvalidRequestError:
            raw_rows = session.execute(select(Parent.id_parent).join(Parent.children)).all()
            raw_ids = [row[0] for row in raw_rows]

        parents_unique = session.scalars(query).unique().all()
        unique_ids = [p.id_parent for p in parents_unique]

        children_count = len(parents_unique[0].children) if parents_unique else 0

    print("inmemory joinedload raw ids:", raw_ids)
    print("inmemory joinedload unique ids:", unique_ids)
    print("inmemory joinedload children count first parent:", children_count)

    return {
        "raw_parent_ids": raw_ids,
        "unique_parent_ids": unique_ids,
        "children_count_first_parent": children_count,
        "expected_sql": (
            "SELECT p.*, c.* FROM demo_parent_joinedload p "
            "LEFT OUTER JOIN demo_child_joinedload c ON c.id_parent = p.id_parent"
        ),
    }


def _build_swagger_spec():
    backend_url = urlparse(current_app.config.get("API_ENDPOINT", ""))
    module_config = current_app.config.get(MODULE_CODE, {})
    module_api = module_config.get("MODULE_API", f"/{MODULE_CODE.lower()}")
    base_path = backend_url.path.rstrip("/")
    if base_path:
        base_path = f"{base_path}{module_api}"
    else:
        base_path = module_api

    schemes = [backend_url.scheme] if backend_url.scheme else ["https", "http"]
    spec = {
        "swagger": "2.0",
        "info": {
            "version": "0.1.0",
            "title": "Demo module API",
            "description": "Swagger documentation for the Demo module endpoints.",
        },
        "basePath": base_path,
        "schemes": schemes,
        "produces": ["application/json"],
        "consumes": ["application/json"],
        "tags": [
            {"name": "Demo", "description": "Demo endpoints"},
        ],
        "definitions": {
            "Demo": {
                "type": "object",
                "properties": {
                    "id_demo": {"type": "integer", "format": "int32"},
                },
                "required": ["id_demo"],
            },
            "Error": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "error": {"type": "string"},
                },
            },
        },
        "securityDefinitions": {
            "bearerAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}
        },
        "security": [{"bearerAuth": []}],
        "paths": {
            "/": {
                "get": {
                    "tags": ["Demo"],
                    "summary": "List demos",
                    "responses": {
                        "200": {
                            "description": "Demo list",
                            "schema": {"type": "array", "items": {"$ref": "#/definitions/Demo"}},
                        },
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden"},
                        "500": {"description": "Internal Server Error"},
                    },
                }
            },
            "/{id_demo}": {
                "get": {
                    "tags": ["Demo"],
                    "summary": "Get one demo",
                    "parameters": [
                        {
                            "name": "id_demo",
                            "in": "path",
                            "required": True,
                            "type": "integer",
                            "format": "int32",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Demo item",
                            "schema": {"$ref": "#/definitions/Demo"},
                        },
                        "404": {"description": "Demo not found"},
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden"},
                        "500": {"description": "Internal Server Error"},
                    },
                }
            },
        },
    }

    if backend_url.netloc:
        spec["host"] = backend_url.netloc

    return spec


## ########################################################################
## SWAGGER
## ########################################################################


@blueprint.route("/swagger", methods=["GET"])
@blueprint.route("/swagger/", methods=["GET"])
def swagger_ui():
    return render_template("swagger/index.html", spec_url=url_for("demo.swagger_ressources"))


@blueprint.route("/swagger-ressources", methods=["GET"])
@blueprint.route("/swagger-ressources/", methods=["GET"])
def swagger_ressources():
    return jsonify(_build_swagger_spec())


## ########################################################################
## DEMO - CORE
## ########################################################################


@blueprint.route("/", methods=["GET"])
@login_required
@json_resp
def list_demos():
    # Order by
    query = db.select(Demo)
    demos = db.session.execute(query).scalars().all()
    return demo_list_schema.dump(demos)


@blueprint.route("/<int(signed=True):id_demo>", methods=["GET"])
@login_required
@json_resp
def demo(id_demo):
    query = db.select(Demo)
    demo = db.session.scalars(query.filter_by(id_demo=id_demo)).unique().one_or_none()
    if demo is None:
        raise NotFound(f"Demo {id_demo} not found")
    return demo_schema.dump(demo)


## ########################################################################
## INDIVIDUALS - CRUD
## ########################################################################


@blueprint.route("/individuals", methods=["GET"])
@login_required
@json_resp
def list_individuals():
    schema = IndividualsSchema(as_geojson=True, only=["taxref"])
    limit = request.args.get("limit", type=int, default=50)
    page = request.args.get("page", type=int, default=1)
    filters = _load_individual_filters()
    with _sql_debug("individuals"):
        pagination = repo_paginate_individuals_with_taxref(
            page=page,
            per_page=limit,
            load_strategy="selectin",
            filters=filters,
        )
    items = [_feature_to_individual_payload(schema.dump(item)) for item in pagination["items"]]
    return {
        "items": items,
        "page": pagination["page"],
        "per_page": pagination["per_page"],
        "pages": pagination["pages"],
        "total": pagination["total"],
        "prev_num": pagination["prev_num"],
        "next_num": pagination["next_num"],
    }


@blueprint.route("/individuals/geojson", methods=["GET"])
@login_required
@json_resp
def list_individuals_geojson():
    schema = IndividualsSchema(as_geojson=True, only=["taxref"])
    filters = _load_individual_filters()
    with _sql_debug("individuals-geojson"):
        individuals = repo_list_individuals_for_map(load_strategy="selectin", filters=filters)

    features = []
    for individual in individuals:
        payload = _feature_to_individual_payload(schema.dump(individual))
        feature = _individual_payload_to_feature(payload)
        feature["id"] = payload.get("id_individual")
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@blueprint.route("/individuals", methods=["POST"])
@login_required
@json_resp
def create_individual():
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequest("JSON body is required")
    if "id_individual" in payload:
        raise BadRequest("id_individual must be generated by the server")
    schema = IndividualsSchema(as_geojson=True)
    individual = schema.load(_individual_payload_to_feature(payload))
    with _sql_debug("individuals-create"):
        individual = repo_create_individual(individual)
    return _feature_to_individual_payload(schema.dump(individual))


@blueprint.route("/individuals/validate", methods=["POST"])
@login_required
@json_resp
def validate_individual():
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequest("JSON body is required")
    schema = IndividualsSchema(as_geojson=True)
    try:
        schema.load(_individual_payload_to_feature(payload), partial=True)
    except ValidationError as exc:
        return {"valid": False, "errors": exc.messages}, 422
    return {"valid": True}


@blueprint.route("/individuals/<int:id_individual>", methods=["PUT"])
@login_required
@json_resp
def update_individual(id_individual):
    individual = db.session.get(Individuals, id_individual)
    if individual is None:
        raise NotFound(f"Individual {id_individual} not found")
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequest("JSON body is required")
    if "id_individual" in payload:
        raise BadRequest("id_individual must be provided in the URL, not in the request body")
    schema = IndividualsSchema(as_geojson=True)
    individual = schema.load(_individual_payload_to_feature(payload), instance=individual, partial=True)
    with _sql_debug("individuals-update"):
        repo_update_individual()
    return _feature_to_individual_payload(schema.dump(individual))


@blueprint.route("/individuals/<int:id_individual>", methods=["DELETE"])
@login_required
@json_resp
def delete_individual(id_individual):
    individual = db.session.get(Individuals, id_individual)
    if individual is None:
        raise NotFound(f"Individual {id_individual} not found")
    with _sql_debug("individuals-delete"):
        repo_delete_individual(individual)
    return {"status": "deleted", "id_individual": id_individual}


@blueprint.route("/individual-tags", methods=["GET"])
@login_required
@json_resp
def list_individual_tags():
    return individual_tag_list_schema.dump(repo_list_individual_tags())


@blueprint.route("/individuals/form-m2m", methods=["POST"])
@login_required
@json_resp
def create_individual_form_m2m():
    payload = _load_individual_form_m2m_payload()
    tag_ids = payload.pop("tag_ids")
    schema = IndividualsSchema(as_geojson=True)
    response_schema = IndividualsSchema(as_geojson=True, only=["taxref", "tags"])
    individual = schema.load(_individual_payload_to_feature(payload))
    try:
        tags = repo_get_individual_tags_by_ids(tag_ids)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    with _sql_debug("individuals-form-m2m-create"):
        individual = repo_save_individual_with_tags(individual, tags)
    return _feature_to_individual_payload(response_schema.dump(individual))


@blueprint.route("/individuals/form-m2m/<int:id_individual>", methods=["PUT"])
@login_required
@json_resp
def update_individual_form_m2m(id_individual):
    individual = repo_get_individual_with_taxref_and_tags(id_individual)
    if individual is None:
        raise NotFound(f"Individual {id_individual} not found")
    payload = _load_individual_form_m2m_payload()
    tag_ids = payload.pop("tag_ids")
    schema = IndividualsSchema(as_geojson=True)
    response_schema = IndividualsSchema(as_geojson=True, only=["taxref", "tags"])
    individual = schema.load(_individual_payload_to_feature(payload), instance=individual, partial=True)
    try:
        tags = repo_get_individual_tags_by_ids(tag_ids)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    with _sql_debug("individuals-form-m2m-update"):
        individual = repo_save_individual_with_tags(individual, tags)
    return _feature_to_individual_payload(response_schema.dump(individual))


## ########################################################################
## EXAMPLES
## ########################################################################


@blueprint.route("/examples/individuals/manual", methods=["GET"])
@login_required
@json_resp
def list_individuals_manual():
    with _sql_debug("manual"):
        individuals = repo_list_individuals_with_taxref(load_strategy="joined")
    print("manual serialization count:", len(individuals))
    return _serialize_individuals_manual(individuals)


@blueprint.route("/examples/individuals/schema", methods=["GET"])
@login_required
@json_resp
def list_individuals_schema():
    with _sql_debug("schema"):
        individuals = repo_list_individuals_with_taxref(load_strategy="joined")
    schema = IndividualsSchema(only=["id_individual", "name_individual", "cd_nom", "taxref"])
    result = schema.dump(individuals, many=True)
    print("schema serialization count:", len(result))
    return result


@blueprint.route("/examples/mock/calls", methods=["GET"])
@login_required
@json_resp
def demo_mock_calls():
    strategies = request.args.getlist("strategy") or ["joined", "selectin"]
    results = []
    for strategy in strategies:
        individuals = repo_list_individuals_with_taxref(load_strategy=strategy)
        results.append({"strategy": strategy, "count": len(individuals)})
    return {"strategies": results}


@blueprint.route("/examples/mock/args", methods=["GET"])
@login_required
@json_resp
def demo_mock_args():
    try:
        a = int(request.args.get("a", 1))
        b = int(request.args.get("b", 2))
    except ValueError as exc:
        raise BadRequest("a and b must be integers") from exc
    return repo_compute_demo_stats(a, b)


@blueprint.route("/examples/mock/error", methods=["GET"])
@login_required
@json_resp
def demo_mock_error():
    should_fail = request.args.get("fail", "false").lower() in {"1", "true", "yes"}
    try:
        result = repo_raise_for_demo(should_fail)
    except Exception as exc:
        raise BadRequest(str(exc)) from exc
    return result


@blueprint.route("/examples/loading/joinedload", methods=["GET"])
@login_required
@json_resp
def list_individuals_joinedload():
    query = db.select(Individuals).options(joinedload(Individuals.taxref))
    with _sql_debug("joinedload"):
        individuals = db.session.scalars(query).unique().all()
    first = individuals[0] if individuals else None
    loaded = first is not None and "taxref" in first.__dict__
    print("joinedload loaded taxref before access:", loaded)
    return {
        "count": len(individuals),
        "taxref_loaded_first": loaded,
    }


@blueprint.route("/examples/loading/selectinload", methods=["GET"])
@login_required
@json_resp
def list_individuals_selectinload():
    query = db.select(Individuals).options(selectinload(Individuals.taxref))
    with _sql_debug("selectinload"):
        individuals = db.session.scalars(query).all()
    first = individuals[0] if individuals else None
    loaded = first is not None and "taxref" in first.__dict__
    print("selectinload loaded taxref before access:", loaded)
    return {
        "count": len(individuals),
        "taxref_loaded_first": loaded,
    }


@blueprint.route("/examples/loading/lazy", methods=["GET"])
@login_required
@json_resp
def list_individuals_lazy():
    query = db.select(Individuals)
    with _sql_debug("lazy"):
        individuals = db.session.scalars(query).all()
    first = individuals[0] if individuals else None
    loaded_before = first is not None and "taxref" in first.__dict__
    taxref_name = None
    if first:
        with _sql_debug("lazy-access"):
            taxref = first.taxref
        loaded_after = "taxref" in first.__dict__
        taxref_name = getattr(taxref, "nom_complet", None) if taxref else None
    else:
        loaded_after = False
    print("lazy loaded before access:", loaded_before)
    print("lazy loaded after access:", loaded_after)
    return {
        "count": len(individuals),
        "taxref_loaded_before": loaded_before,
        "taxref_loaded_after": loaded_after,
        "taxref_name_first": taxref_name,
    }


@blueprint.route("/examples/loading/noload", methods=["GET"])
@login_required
@json_resp
def list_individuals_noload():
    query = db.select(Individuals).options(noload(Individuals.taxref))
    with _sql_debug("noload"):
        individuals = db.session.scalars(query).all()
    first = individuals[0] if individuals else None
    loaded = first is not None and "taxref" in first.__dict__
    taxref_value = None
    if first is not None:
        taxref_value = None if first.taxref is None else {"cd_nom": first.taxref.cd_nom}
    print("noload loaded taxref:", loaded)
    return {
        "count": len(individuals),
        "taxref_loaded_first": loaded,
        "taxref_value_first": taxref_value,
    }


@blueprint.route("/examples/loading/defer", methods=["GET"])
@login_required
@json_resp
def list_individuals_defer():
    query = db.select(Individuals).options(defer(Individuals.name_individual))
    with _sql_debug("defer"):
        individuals = db.session.scalars(query).all()
    first = individuals[0] if individuals else None
    loaded_before = first is not None and "name_individual" in first.__dict__
    name_value = None
    if first:
        with _sql_debug("defer-access"):
            name_value = first.name_individual
        loaded_after = "name_individual" in first.__dict__
    else:
        loaded_after = False
    print("defer loaded before access:", loaded_before)
    print("defer loaded after access:", loaded_after)
    return {
        "count": len(individuals),
        "name_loaded_before": loaded_before,
        "name_loaded_after": loaded_after,
        "name_first": name_value,
    }


@blueprint.route("/examples/query/load-only", methods=["GET"])
@login_required
@json_resp
def demo_query_load_only():
    query = db.select(Individuals).options(
        load_only(Individuals.id_individual, Individuals.name_individual)
    )
    with _sql_debug("load-only"):
        individuals = db.session.scalars(query).all()
    first = individuals[0] if individuals else None
    loaded_before = first is not None and "cd_nom" in first.__dict__
    cd_nom_value = None
    if first is not None:
        with _sql_debug("load-only-access"):
            cd_nom_value = first.cd_nom
    loaded_after = first is not None and "cd_nom" in first.__dict__
    print("load_only first type:", type(first))
    print("load_only cd_nom loaded before:", loaded_before)
    print("load_only cd_nom loaded after:", loaded_after)
    return {
        "count": len(individuals),
        "first_type": str(type(first)),
        "cd_nom_loaded_before": loaded_before,
        "cd_nom_loaded_after": loaded_after,
        "cd_nom_first": cd_nom_value,
    }


@blueprint.route("/examples/query/select-columns", methods=["GET"])
@login_required
@json_resp
def demo_query_select_columns():
    with _sql_debug("select-columns"):
        rows = repo_list_individuals_projection()
    first = rows[0] if rows else None
    mapping = dict(first._mapping) if first else {}
    print("select-columns first type:", type(first))
    print("select-columns mapping keys:", list(mapping.keys()))
    return {
        "count": len(rows),
        "first_type": str(type(first)),
        "first_values": list(first) if first else [],
        "first_mapping": mapping,
    }


@blueprint.route("/examples/loading/annotated", methods=["GET"])
@login_required
@json_resp
def demo_loading_annotated():
    # lazy load: aucun eager load configure
    lazy_query = db.select(Individuals)
    # lazy load: requete ORM sans option de chargement
    with _sql_debug("annotated-lazy"):
        lazy_items = db.session.scalars(lazy_query).all()
    # lazy load: relation non chargee tant qu'on n'y accede pas
    lazy_loaded = bool(lazy_items) and ("taxref" in lazy_items[0].__dict__)

    # joinedload: eager load via JOIN dans la requete principale
    joined_query = db.select(Individuals).options(joinedload(Individuals.taxref))
    # joinedload: relation chargee tout de suite
    with _sql_debug("annotated-joinedload"):
        joined_items = db.session.scalars(joined_query).unique().all()
    # joinedload: relation presente avant acces
    joined_loaded = bool(joined_items) and ("taxref" in joined_items[0].__dict__)

    # selectinload: eager load via requete secondaire IN
    selectin_query = db.select(Individuals).options(selectinload(Individuals.taxref))
    # selectinload: relation chargee apres la requete secondaire
    with _sql_debug("annotated-selectinload"):
        selectin_items = db.session.scalars(selectin_query).all()
    # selectinload: relation presente avant acces
    selectin_loaded = bool(selectin_items) and ("taxref" in selectin_items[0].__dict__)

    # noload: relation jamais chargee
    noload_query = db.select(Individuals).options(noload(Individuals.taxref))
    # noload: relation forcee a ne pas charger
    with _sql_debug("annotated-noload"):
        noload_items = db.session.scalars(noload_query).all()
    # noload: relation absente meme apres acces
    noload_loaded = bool(noload_items) and ("taxref" in noload_items[0].__dict__)

    # defer: colonne chargee seulement a l'acces
    defer_query = db.select(Individuals).options(defer(Individuals.name_individual))
    # defer: la colonne name_individual est retardee
    with _sql_debug("annotated-defer"):
        defer_items = db.session.scalars(defer_query).all()
    # defer: colonne absente avant acces
    defer_loaded_before = bool(defer_items) and ("name_individual" in defer_items[0].__dict__)
    # defer: acces declenche le chargement
    if defer_items:
        with _sql_debug("annotated-defer-access"):
            _ = defer_items[0].name_individual
    # defer: colonne presente apres acces
    defer_loaded_after = bool(defer_items) and ("name_individual" in defer_items[0].__dict__)

    return {
        "lazy_loaded_before_access": lazy_loaded,
        "joinedload_loaded_before_access": joined_loaded,
        "selectinload_loaded_before_access": selectin_loaded,
        "noload_loaded_before_access": noload_loaded,
        "defer_loaded_before_access": defer_loaded_before,
        "defer_loaded_after_access": defer_loaded_after,
    }


@blueprint.route("/examples/individuals/export-csv", methods=["GET"])
@login_required
def export_individuals_csv():
    with _sql_debug("export-csv"):
        rows = repo_list_individuals_csv_rows()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id_individual", "name_individual", "cd_nom"])
    writer.writerows(rows)
    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=individuals.csv"},
    )


@blueprint.route("/examples/individuals/count-by-taxref", methods=["GET"])
@login_required
@json_resp
def count_individuals_by_taxref():
    with _sql_debug("count-by-taxref"):
        rows = repo_count_individuals_by_taxref()
    return [{"cd_nom": cd_nom, "count": count} for cd_nom, count in rows]


def _taxref_autocomplete_payload():
    q = request.args.get("q", "").strip()
    if not q:
        return []
    limit = request.args.get("limit", type=int) or 10
    with _sql_debug("autocomplete"):
        rows = repo_search_taxref_autocomplete(q, limit=limit)
    payload = [{"cd_nom": cd_nom, "nom_complet": nom_complet} for cd_nom, nom_complet in rows]
    return taxref_autocomplete_schema.dump(payload)


@blueprint.route("/taxref/autocomplete", methods=["GET"])
@login_required
@json_resp
def taxref_autocomplete():
    return _taxref_autocomplete_payload()


@blueprint.route("/examples/taxref/autocomplete", methods=["GET"])
@login_required
@json_resp
def taxref_autocomplete_legacy():
    return _taxref_autocomplete_payload()


@blueprint.route("/examples/relationships/backref", methods=["GET"])
@login_required
@json_resp
def demo_backref():
    parent, child = _build_backref_demo()
    return {
        "parent": {
            "id_parent": parent.id_parent,
            "name": parent.name,
            "children_count": len(parent.children),
        },
        "child": {
            "id_child": child.id_child,
            "name": child.name,
            "parent_name": child.parent.name if child.parent else None,
        },
        "notes": "backref auto-creates the reverse attribute on Child.",
    }


@blueprint.route("/examples/relationships/back-populates", methods=["GET"])
@login_required
@json_resp
def demo_back_populates():
    parent, child = _build_back_populates_demo()
    return {
        "parent": {
            "id_parent": parent.id_parent,
            "name": parent.name,
            "children_count": len(parent.children),
        },
        "child": {
            "id_child": child.id_child,
            "name": child.name,
            "parent_name": child.parent.name if child.parent else None,
        },
        "notes": "back_populates requires explicit attributes on both sides.",
    }


@blueprint.route("/examples/inmemory/joinedload-parent-children", methods=["GET"])
@login_required
@json_resp
def demo_inmemory_joinedload_parent_children():
    return _build_inmemory_joinedload_demo()
