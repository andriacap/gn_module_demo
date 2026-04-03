"""
Définition des routes du module export
"""

# import logging

from geonature.core.imports.checks.dataframe import geometry
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from flask import Blueprint, request
from werkzeug.exceptions import NotFound, BadRequest

from geonature.core.gn_permissions import decorators as permissions
from geonature.core.gn_permissions.decorators import login_required
from geonature.utils.env import db
from utils_flask_sqla.response import json_resp

from . import MODULE_CODE
from .models import Demo, Individual
from apptax.taxonomie.models import Taxref
from .schemas import IndividualSchema

# A utiliser pour stocker les logs dans le fichier de log
# logger = logging.getLogger(__name__)
blueprint = Blueprint("demo", __name__, cli_group="demo")

## ########################################################################
## COLLECTION
## ########################################################################


@blueprint.route("/", methods=["GET"])
@login_required
@json_resp
def list_demos():
    # Order by
    query = db.select(Demo)
    demos = db.session.execute(query).scalars().all()
    return [{"id_demo": demo.id_demo} for demo in demos]


## ########################################################################
## ENTITY - GET
## ########################################################################


@blueprint.route("/<int(signed=True):id_demo>", methods=["GET"])
@login_required
@json_resp
def demo(id_demo):
    query = db.select(Demo)
    demo = db.session.scalars(query.filter_by(id_demo=id_demo)).unique().one_or_none()
    if demo is None:
        raise NotFound(f"Demo {id_demo} not found")
    return {"id_demo": demo.id_demo}


# ########################################################################
# Avec sérialiseur marshmallow
#
@blueprint.route("/indiv", methods=["GET"])
@login_required
@json_resp
def list_indiv():
    # Un schéma doit être créé : version sans nomenclatures
    # schema = IndividualSchema(many=True, only=["taxref"])
    # query = db.select(Individual).options(joinedload(Individual.taxref))

    # Un schéma doit être créé : version avec nomenclatures
    nomenclatures = list(Individual.__nomenclatures__)

    # Construire la liste des champs de type nomenclature à sérialiser
    nomenclatures_fields = [n for n in nomenclatures]
      
    # Construire le schéma en incluant dynamiquement seulement les champs de type nomenclature et taxref
    schema = IndividualSchema(only=["taxref"] + nomenclatures_fields)

    # Construire la requête en incluant les jointures nécessaires pour éviter les problèmes de N+1
    # Sans pagination
    # query = db.select(Individual).options(joinedload(Individual.taxref),*[joinedload(getattr(Individual, f)) for f in nomenclatures_fields])

    # Avec pagination
    per_page = request.args.get("limit", type=int, default=50)
    page = request.args.get("page", type=int, default=1)

    page = max(1, int(page))
    per_page = max(1, int(per_page))

    total = db.session.scalar(db.select(func.count(Individual.id_individual))) or 0
    query = (
        db.select(Individual).options(joinedload(Individual.taxref),*[joinedload(getattr(Individual, f)) for f in nomenclatures_fields])
        .order_by(Individual.id_individual.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    # Passer la requête en chaîne de caractères pour les logs
    # sql = query.compile(
    #     dialect=postgresql.dialect(),
    #     compile_kwargs={"literal_binds": True},
    # )

    # print(f"-- DEBUG ------- {sql}")

    # Sans pagination 
    # indivs = db.session.execute(query).scalars().all()

    # print(f"-- DEBUG ------- indivs[n] type : {type(indivs[0])}")
    # print(f"-- DEBUG ------- indivs log: {indivs}")
    # print(f"-- DEBUG ------- tous les indivs: {vars(indivs[0].taxref)}")

    # Avec pagination
    items = db.session.scalars(query).unique().all()
    pages = ((total - 1) // per_page) + 1 if total else 0

    # Sans pagination
    # return schema.dump(indivs,many=True)

    # Avec pagination
    items_serialised = schema.dump(items, many=True)

    paginate_items = {
        "items": items_serialised,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "total": total,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if pages and page < pages else None,
    }

    return paginate_items


@blueprint.route("/indiv/<int(signed=True):id_individual>", methods=["GET"])
@login_required
@json_resp
def indiv(id_individual):
    # Un schéma doit être créé : version avec nomenclatures
    nomenclatures = list(Individual.__nomenclatures__)
    
    # Construire la liste des champs de type nomenclature à sérialiser
    nomenclatures_fields = [n for n in nomenclatures]
      
    # Construire le schéma en incluant dynamiquement seulement les champs de type nomenclature et taxref
    schema = IndividualSchema(as_geojson=True, only=["taxref"] + nomenclatures_fields)

    query = (
        db.select(Individual)
        .options(joinedload(Individual.taxref))
        .filter_by(id_individual=id_individual)
    )

    # Passer la requête en chaîne de caractères pour les logs
    sql = query.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )

    # A utiliser pour stocker les logs dans le fichier de log
    print(f"-- DEBUG ------- {sql}")

    indivs = db.session.execute(query).one_or_none()

    print(f"-- DEBUG ------- indivs log: {indivs}")

    return schema.dump(indivs,many=True)


@blueprint.route("/indiv", methods=["POST"])
@login_required
@json_resp
def create_indiv():
    payload = request.get_json(silent=True)

    if payload is None:
        raise BadRequest("JSON body is required")

    schema = IndividualSchema(as_geojson=True)
    payload = dict(payload or {})
    geometry = payload.pop("geom_local", None)

    payload = {
        "type": "Feature",
        "geometry": geometry,
        "properties": payload,
    }

    individual = schema.load(payload)
    print(f"-- DEBUG ------- individual log: {individual}")

    db.session.add(individual)
    db.session.commit()
    return schema.dump(individual)
