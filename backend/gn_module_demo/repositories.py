from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, selectinload

from apptax.taxonomie.models import Taxref
from geonature.utils.env import db
from pypnusershub.db.models import User

from .models import BibIndividualTag, Individuals


def apply_individual_filters(query, filters=None):
    filters = filters or {}

    name_query = (filters.get("name") or "").strip()
    if name_query:
        query = query.where(Individuals.name_individual.ilike(f"%{name_query}%"))

    taxref_query = (filters.get("taxref_query") or "").strip()
    if taxref_query:
        search = f"%{taxref_query}%"
        query = query.join(Taxref, Individuals.cd_nom == Taxref.cd_nom).where(
            or_(
                Taxref.nom_complet.ilike(search),
                Taxref.nom_vern.ilike(search),
                Taxref.lb_nom.ilike(search),
            )
        )

    observer_query = (filters.get("observer") or "").strip()
    if observer_query:
        observer_id = None
        if observer_query.isdigit():
            observer_id = int(observer_query)

        if observer_id is not None:
            query = query.where(Individuals.observer == observer_id)
        else:
            search = f"%{observer_query}%"
            observer_legacy_expr = func.coalesce(
                Individuals.additional_data["observer"].astext,
                Individuals.additional_data["author"].astext,
                Individuals.additional_data["auteur"].astext,
            )
            query = query.outerjoin(User, Individuals.observer == User.id_role).where(
                or_(
                    User.nom_complet.ilike(search),
                    User.nom_role.ilike(search),
                    User.prenom_role.ilike(search),
                    User.identifiant.ilike(search),
                    observer_legacy_expr.ilike(search),
                )
            )

    observed_date_expr = func.left(
        func.coalesce(
            Individuals.additional_data["observation_date"].astext,
            Individuals.additional_data["date_observation"].astext,
            Individuals.additional_data["observed_at"].astext,
            Individuals.additional_data["date"].astext,
        ),
        10,
    )
    date_from = filters.get("date_from")
    if date_from:
        query = query.where(observed_date_expr >= date_from)

    date_to = filters.get("date_to")
    if date_to:
        query = query.where(observed_date_expr <= date_to)

    return query


def build_individuals_query(load_strategy="joined", filters=None):
    query = db.select(Individuals)
    if load_strategy == "joined":
        query = query.options(
            joinedload(Individuals.taxref),
            joinedload(Individuals.observer_role),
        )
    elif load_strategy == "selectin":
        query = query.options(
            selectinload(Individuals.taxref),
            selectinload(Individuals.observer_role),
        )
    return apply_individual_filters(query, filters=filters)


def list_individuals_with_taxref(load_strategy="joined", filters=None):
    query = build_individuals_query(load_strategy=load_strategy, filters=filters)
    return db.session.scalars(query).unique().all()


def list_individuals_for_map(load_strategy="selectin", filters=None):
    query = (
        build_individuals_query(load_strategy=load_strategy, filters=filters)
        .order_by(Individuals.id_individual.asc())
    )
    return db.session.scalars(query).unique().all()


def paginate_individuals_with_taxref(page=1, per_page=50, load_strategy="selectin", filters=None):
    page = max(1, int(page))
    per_page = max(1, int(per_page))

    count_query = db.select(func.count(Individuals.id_individual)).select_from(Individuals)
    count_query = apply_individual_filters(count_query, filters=filters)
    total = db.session.scalar(count_query) or 0
    query = (
        build_individuals_query(load_strategy=load_strategy, filters=filters)
        .order_by(Individuals.id_individual.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = db.session.scalars(query).unique().all()
    pages = ((total - 1) // per_page) + 1 if total else 0

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "total": total,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if pages and page < pages else None,
    }


def list_individuals_projection():
    query = db.select(Individuals.id_individual, Individuals.name_individual)
    return db.session.execute(query).all()


def list_individuals_csv_rows():
    query = db.select(
        Individuals.id_individual,
        Individuals.name_individual,
        Individuals.cd_nom,
    )
    return db.session.execute(query).all()


def count_individuals_by_taxref():
    count_label = func.count(Individuals.id_individual).label("count")
    query = (
        db.select(Individuals.cd_nom, count_label)
        .group_by(Individuals.cd_nom)
        .order_by(count_label.desc())
    )
    return db.session.execute(query).all()


def search_taxref_autocomplete(query_text, limit=10):
    if not query_text:
        return []
    query = (
        db.select(Taxref.cd_nom, Taxref.nom_complet)
        .where(Taxref.nom_complet.ilike(f"%{query_text}%"))
        .order_by(Taxref.nom_complet.asc())
        .limit(limit)
    )
    return db.session.execute(query).all()


def create_individual(individual):
    db.session.add(individual)
    db.session.commit()
    return individual


def list_individual_tags():
    query = db.select(BibIndividualTag).order_by(BibIndividualTag.label_tag.asc())
    return db.session.scalars(query).all()


def get_individual_tags_by_ids(tag_ids):
    unique_ids = list(dict.fromkeys(tag_ids or []))
    if not unique_ids:
        return []
    query = db.select(BibIndividualTag).where(BibIndividualTag.id_tag.in_(unique_ids))
    tags = db.session.scalars(query).all()
    found_ids = {tag.id_tag for tag in tags}
    missing_ids = sorted(set(unique_ids) - found_ids)
    if missing_ids:
        raise ValueError(f"Unknown tag id(s): {missing_ids}")
    return tags


def get_individual_with_taxref_and_tags(id_individual):
    query = (
        db.select(Individuals)
        .where(Individuals.id_individual == id_individual)
        .options(selectinload(Individuals.taxref), selectinload(Individuals.tags))
    )
    return db.session.scalars(query).unique().one_or_none()


def save_individual_with_tags(individual, tags):
    individual.tags = tags
    db.session.add(individual)
    db.session.commit()
    return individual


def update_individual():
    db.session.commit()


def delete_individual(individual):
    db.session.delete(individual)
    db.session.commit()


def compute_demo_stats(a, b):
    return {"sum": a + b, "product": a * b}


def repo_raise_for_demo(should_fail=False):
    if should_fail:
        raise RuntimeError("Demo repository failure")
    return {"ok": True}
