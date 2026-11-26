"""Tests for parts inventory and catalog search."""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from jlcpcb_cli.cli import cli
from jlcpcb_cli.core.parts import (
    _extract_catalog_component,
    _extract_component,
    parse_attr_filters,
    search_catalog,
)


def test_extract_component():
    comp = {
        "lcscComponentId": 106577,
        "componentCode": "C105362",
        "componentModel": "FMF06FTHR010-LH",
        "componentBrand": "PSA(Prosperity Dielectrics)",
        "componentType": "Resistors",
        "componentSpecification": "1206",
        "description": "10mΩ 1W Current Sense Resistor",
        "privateStockCount": 104,
        "rohsFlag": 1,
    }

    result = _extract_component(comp)

    assert result["lcscPart"] == "C105362"
    assert result["mfrPart"] == "FMF06FTHR010-LH"
    assert result["manufacturer"] == "PSA(Prosperity Dielectrics)"
    assert result["category"] == "Resistors"
    assert result["package"] == "1206"
    assert result["stock"] == 104
    assert result["rohs"] is True


def test_extract_component_no_rohs():
    comp = {
        "componentCode": "C12345",
        "componentModel": "XYZ",
        "rohsFlag": 0,
    }

    result = _extract_component(comp)

    assert result["lcscPart"] == "C12345"
    assert result["rohs"] is False


def test_parse_attr_filters():
    assert parse_attr_filters(["Resistance=10kΩ", "Tolerance=±1%"]) == [
        {"Resistance": ["10kΩ"]},
        {"Tolerance": ["±1%"]},
    ]
    assert parse_attr_filters(["Resistance=10kΩ", "Resistance=4.7kΩ", "Resistance=10kΩ"]) == [
        {"Resistance": ["10kΩ", "4.7kΩ"]},
    ]


def test_parse_attr_filters_invalid():
    with pytest.raises(ValueError, match="expected 'Key=Value'"):
        parse_attr_filters(["Resistance"])
    with pytest.raises(ValueError, match="non-empty"):
        parse_attr_filters(["=10kΩ"])


def test_extract_catalog_component():
    comp = {
        "componentCode": "C25804",
        "componentModelEn": "0603WAF1002T5E",
        "componentBrandEn": "UNI-ROYAL(Uniroyal Elec)",
        "firstSortName": "Resistors",
        "secondSortName": "Chip Resistor - Surface Mount",
        "componentSpecificationEn": "0603",
        "describe": "10kΩ ±1% 1/10W 0603 Chip Resistor",
        "componentLibraryType": "base",
        "stockCount": 500000,
        "minPurchaseNum": 10,
        "componentPrices": [
            {"startNumber": 10, "endNumber": 99, "productPrice": 0.0018},
            {"startNumber": 100, "endNumber": None, "productPrice": 0.0012},
        ],
        "attributes": [
            {"attribute_name_en": "Resistance", "attribute_value_name": "10kΩ"},
            {"attribute_name_en": "Tolerance", "attribute_value_name": "±1%"},
        ],
        "dataManualUrl": "https://example.com/ds.pdf",
    }

    result = _extract_catalog_component(comp)

    assert result["lcscPart"] == "C25804"
    assert result["mfrPart"] == "0603WAF1002T5E"
    assert result["manufacturer"] == "UNI-ROYAL(Uniroyal Elec)"
    assert result["category"] == "Resistors"
    assert result["subcategory"] == "Chip Resistor - Surface Mount"
    assert result["package"] == "0603"
    assert result["libraryType"] == "basic"
    assert result["stock"] == 500000
    assert result["minOrderQty"] == 10
    assert result["prices"] == [
        {"minQty": 10, "maxQty": 99, "unitPrice": 0.0018},
        {"minQty": 100, "maxQty": None, "unitPrice": 0.0012},
    ]
    assert result["attributes"] == {"Resistance": "10kΩ", "Tolerance": "±1%"}
    assert result["datasheetUrl"] == "https://example.com/ds.pdf"


def test_search_catalog_payload_and_response():
    client = MagicMock()
    client.api_post.return_value = {
        "code": 200,
        "data": {
            "componentPageInfo": {
                "currentPage": 2,
                "pageSize": 10,
                "total": 42,
                "list": [
                    {
                        "componentCode": "C25804",
                        "componentModelEn": "0603WAF1002T5E",
                        "componentLibraryType": "expand",
                        "stockCount": 120,
                    }
                ],
            }
        },
    }

    result = search_catalog(
        client,
        keyword="C25804",
        page=2,
        limit=10,
        library_type="extended",
        in_stock=True,
        min_stock=100,
        category="Resistors",
        subcategory="Chip Resistor - Surface Mount",
        packages=["0603"],
        brands=["UNI-ROYAL"],
        attributes=[{"Resistance": ["10kΩ"]}],
    )

    client.api_post.assert_called_once()
    path, payload = client.api_post.call_args[0]
    assert path == "/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2"
    assert payload["keyword"] == "C25804"
    assert payload["currentPage"] == 2
    assert payload["pageSize"] == 10
    assert payload["componentLibraryType"] == "expand"
    assert payload["stockFlag"] is True
    assert payload["startStockNumber"] == 100
    assert payload["firstSortName"] == "Resistors"
    assert payload["secondSortName"] == "Chip Resistor - Surface Mount"
    assert payload["componentSpecificationList"] == ["0603"]
    assert payload["componentBrandList"] == ["UNI-ROYAL"]
    assert payload["componentAttributeList"] == [{"Resistance": ["10kΩ"]}]

    assert result["pagination"] == {"page": 2, "pageSize": 10, "total": 42}
    assert len(result["components"]) == 1
    assert result["components"][0]["libraryType"] == "extended"


def test_cli_parts_search(monkeypatch):
    mock_client = MagicMock()
    mock_client.api_post.return_value = {
        "code": 200,
        "data": {
            "componentPageInfo": {
                "currentPage": 1,
                "pageSize": 25,
                "total": 1,
                "list": [{"componentCode": "C25804", "componentLibraryType": "base"}],
            }
        },
    }
    monkeypatch.setattr("jlcpcb_cli.cli.get_web_client", lambda: mock_client)

    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            "parts",
            "search",
            "C25804",
            "--library-type",
            "basic",
            "--in-stock",
            "--package",
            "0603",
            "--attr",
            "Resistance=10kΩ",
        ],
    )

    assert res.exit_code == 0, res.output
    assert '"lcscPart": "C25804"' in res.output
    _, payload = mock_client.api_post.call_args[0]
    assert payload["componentLibraryType"] == "base"
    assert payload["stockFlag"] is True
    assert payload["componentSpecificationList"] == ["0603"]
    assert payload["componentAttributeList"] == [{"Resistance": ["10kΩ"]}]
