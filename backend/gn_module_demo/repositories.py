from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from apptax.taxonomie.models import Taxref
from geonature.utils.env import db

from .models import BibIndividualTag, Individuals


def build_individuals_query(load_strategy="joined"):
    query = db.select(Individuals)
    if load_strategy == "joined":
        query = query.options(joinedload(Individuals.taxref))
    elif load_strategy == "selectin":
        query = query.options(selectinload(Individuals.taxref))
    return query


def list_individuals_with_taxref(load_strategy="joined"):
    query = build_individuals_query(load_strategy=load_strategy)
    return db.session.scalars(query).unique().all()


def paginate_individuals_with_taxref(page=1, per_page=50, load_strategy="selectin"):
    page = max(1, int(page))
    per_page = max(1, int(per_page))

    total = db.session.scalar(db.select(func.count(Individuals.id_individual))) or 0
    query = (
        build_individuals_query(load_strategy=load_strategy)
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
