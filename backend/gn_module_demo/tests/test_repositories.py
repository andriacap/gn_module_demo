import pytest

from geonature.utils.env import db

from gn_module_demo.models import Individuals
from gn_module_demo.repositories import (
    count_individuals_by_taxref,
    create_individual,
    delete_individual,
    get_individual_tags_by_ids,
    list_individual_tags,
    list_individuals_csv_rows,
    list_individuals_projection,
    list_individuals_with_taxref,
    paginate_individuals_with_taxref,
    save_individual_with_tags,
    search_taxref_autocomplete,
    update_individual,
)


@pytest.mark.db
def test_list_individuals_with_taxref_returns_items(individuals_batch):
    individuals = list_individuals_with_taxref(load_strategy="joined")

    assert len(individuals) >= len(individuals_batch)
    assert hasattr(individuals[0], "taxref")


@pytest.mark.db
def test_paginate_individuals_with_taxref_returns_page(individuals_batch):
    pagination = paginate_individuals_with_taxref(page=1, per_page=2, load_strategy="selectin")

    assert pagination["page"] == 1
    assert pagination["per_page"] == 2
    assert pagination["total"] >= len(individuals_batch)
    assert isinstance(pagination["items"], list)
    if pagination["items"]:
        assert hasattr(pagination["items"][0], "taxref")


@pytest.mark.db
def test_list_individuals_projection_returns_rows(individuals_batch):
    rows = list_individuals_projection()

    assert len(rows) >= len(individuals_batch)
    assert len(rows[0]) == 2


@pytest.mark.db
def test_list_individuals_csv_rows_returns_rows(individuals_batch):
    rows = list_individuals_csv_rows()

    assert len(rows) >= len(individuals_batch)
    assert len(rows[0]) == 3


@pytest.mark.db
def test_count_individuals_by_taxref_includes_new(individuals_batch):
    rows = count_individuals_by_taxref()
    counts = {cd_nom: count for cd_nom, count in rows}
    cd_nom = individuals_batch[0].cd_nom

    assert counts.get(cd_nom, 0) >= len(individuals_batch)


@pytest.mark.db
def test_search_taxref_autocomplete_empty_returns_empty():
    assert search_taxref_autocomplete("") == []


@pytest.mark.db
def test_search_taxref_autocomplete_respects_limit(taxref_sample):
    query = (taxref_sample.nom_complet or "").strip()
    if not query:
        pytest.skip("Taxref.nom_complet vide: impossible de tester l'autocomplete.")
    query = query[:3]

    results = search_taxref_autocomplete(query, limit=1)

    assert len(results) <= 1
    if results:
        cd_nom, nom_complet = results[0]
        assert cd_nom is not None
        assert nom_complet


@pytest.mark.db
def test_list_individual_tags_returns_rows(individual_tags):
    tags = list_individual_tags()
    assert len(tags) >= len(individual_tags)


@pytest.mark.db
def test_get_individual_tags_by_ids_returns_expected(individual_tags):
    ids = [individual_tags[0].id_tag]
    tags = get_individual_tags_by_ids(ids)
    assert [tag.id_tag for tag in tags] == ids


@pytest.mark.db
def test_get_individual_tags_by_ids_raises_on_missing():
    with pytest.raises(ValueError):
        get_individual_tags_by_ids([-99999])


@pytest.mark.db
def test_save_individual_with_tags(individual_in_db, individual_tags):
    saved = save_individual_with_tags(individual_in_db, [individual_tags[0]])
    assert {tag.id_tag for tag in saved.tags} == {individual_tags[0].id_tag}


@pytest.mark.db
def test_create_update_delete_individual(individual_payload):
    individual = Individuals(**individual_payload)

    created = create_individual(individual)
    created_id = created.id_individual

    created.name_individual = "Updated Name"
    update_individual()

    updated = db.session.get(Individuals, created_id)
    assert updated.name_individual == "Updated Name"

    delete_individual(updated)
    assert db.session.get(Individuals, created_id) is None
