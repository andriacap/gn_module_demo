import pytest
from flask import url_for
from pypnusershub.tests.utils import logged_user


def test_demo_list_returns_list(client, users):
    with logged_user(client, users["admin_user"]):
        response = client.get(url_for("demo.list_demos"))

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)


def test_demo_get_not_found(client, users):
    with logged_user(client, users["admin_user"]):
        response = client.get(url_for("demo.indiv", id_demo=-1))

    assert response.status_code == 404

@pytest.mark.usefixtures("client_class")
class TestIndividuals:

    def test_get_individuals(self, users):
        with logged_user(self.client, users["admin_user"]):
            response = self.client.get(url_for("demo.list_indiv"))
        assert response.status_code == 200
    #     individuals = install_module_test_indi
    #     id_individuals = [i.id_individual for i in individuals]

    #     # Test get with default sort
    #     response = self.client.get(url_for("monitorings.get_individuals", module_code="test_indi"))
    #     assert response.status_code == 200
    #     individuals_response = response.json["items"]

    #     assert len(individuals_response) == len(individuals)
    #     assert individuals_response[0]["id_individual"] == max(id_individuals)

    #     # Test sort asc
    #     response = self.client.get(
    #         url_for("monitorings.get_individuals", module_code="test_indi", sort_dir="asc")
    #     )
    #     individuals_response = response.json["items"]

    #     assert individuals_response[0]["id_individual"] == min(id_individuals)

    #     # Test sort other column
    #     response = self.client.get(
    #         url_for(
    #             "monitorings.get_individuals",
    #             module_code="test_indi",
    #             sort="comment",
    #             sort_dir="asc",
    #         )
    #     )
    #     individuals_response = response.json["items"]
    #     assert len(individuals_response) == len(individuals)
    #     assert individuals_response[0]["comment"] == "A Super lézard"

    #     # Test filter main column
    #     response = self.client.get(
    #         url_for("monitorings.get_individuals", module_code="test_indi", id_digitiser="Bob")
    #     )
    #     individuals_response = response.json["items"]
    #     assert len(individuals_response) == 2
    #     assert individuals_response[0]["id_digitiser"] == users["user"].id_role

    #     # Test filter cd_nom column
    #     response = self.client.get(
    #         url_for("monitorings.get_individuals", module_code="test_indi", cd_nom=649883)
    #     )
    #     individuals_response = response.json["items"]
    #     assert len(individuals_response) == 1
    #     assert individuals_response[0]["cd_nom"] == 649883

    #     response = self.client.get(
    #         url_for("monitorings.get_individuals", module_code="test_indi", cd_nom="python")
    #     )
    #     individuals_response = response.json["items"]
    #     assert len(individuals_response) == 1
    #     assert individuals_response[0]["cd_nom"] == 649883

    # def test_get_individuals_scope_1(self, install_module_test_indi, users):
    #     set_logged_user_cookie(self.client, users["self_user"])
    #     response = self.client.get(url_for("monitorings.get_individuals", module_code="test_indi"))
    #     assert response.status_code == 200
    #     assert len(response.json["items"]) == 1

    # def test_get_individuals_scope_2(self, install_module_test_indi, users):
    #     set_logged_user_cookie(self.client, users["stranger_user"])

    #     response = self.client.get(url_for("monitorings.get_individuals", module_code="test_indi"))
    #     assert response.status_code == 200
    #     assert len(response.json["items"]) == 1

    # def test_get_individuals_scope_2_organism(self, install_module_test_indi, users):
    #     set_logged_user_cookie(self.client, users["user"])
    #     response = self.client.get(url_for("monitorings.get_individuals", module_code="test_indi"))
    #     assert response.status_code == 200
    #     assert len(response.json["items"]) == 4
