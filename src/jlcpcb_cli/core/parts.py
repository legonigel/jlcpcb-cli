"""Parts inventory and catalog search at JLCPCB via web API."""

import time

from jlcpcb_cli.core.web_client import WebClient

_INVENTORY_PATH = (
    "/overseas-smt-component-order-platform/v1"
    "/overseasSmtComponentOrder/myLibrary/getCustomerComponentStock"
)
_CATALOG_SEARCH_PATH = (
    "/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2"
)

_LIBRARY_TYPE_MAP = {
    "all": None,
    "basic": "base",
    "extended": "expand",
}


def list_inventory(
    client: WebClient,
    *,
    search: str = "",
    page: int = 1,
    limit: int = 30,
) -> dict:
    """List components stored at JLCPCB."""
    result = client.api_get(
        _INVENTORY_PATH,
        {
            "pageNum": str(page),
            "pageSize": str(limit),
            "keyWord": search,
            "_t": str(int(time.time() * 1000)),
        },
    )

    data = result.get("data") or {}
    items = data.get("list") or []

    return {
        "pagination": {
            "page": page,
            "pageSize": limit,
            "total": data.get("total", 0),
        },
        "components": [_extract_component(c) for c in items],
    }


def _extract_component(comp: dict) -> dict:
    return {
        "lcscPart": comp.get("componentCode"),
        "mfrPart": comp.get("componentModel"),
        "manufacturer": comp.get("componentBrand"),
        "category": comp.get("componentType"),
        "package": comp.get("componentSpecification"),
        "description": comp.get("description"),
        "stock": comp.get("privateStockCount"),
        "rohs": bool(comp.get("rohsFlag")),
    }


def parse_attr_filters(attrs: tuple[str, ...] | list[str]) -> list[dict[str, list[str]]]:
    """Parse 'Key=Value' attribute filter strings into JLCPCB's componentAttributeList."""
    grouped: dict[str, list[str]] = {}
    for item in attrs:
        if "=" not in item:
            raise ValueError(f"Invalid attribute filter {item!r}: expected 'Key=Value'")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise ValueError(f"Invalid attribute filter {item!r}: key and value must be non-empty")
        grouped.setdefault(key, [])
        if value not in grouped[key]:
            grouped[key].append(value)
    return [{k: v} for k, v in grouped.items()]


def search_catalog(
    client: WebClient,
    *,
    keyword: str = "",
    page: int = 1,
    limit: int = 25,
    library_type: str = "all",
    in_stock: bool = False,
    min_stock: int | None = None,
    max_stock: int | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    packages: list[str] | None = None,
    brands: list[str] | None = None,
    attributes: list[dict[str, list[str]]] | None = None,
) -> dict:
    """Search JLCPCB's full SMT parts catalog."""
    payload = {
        "currentPage": page,
        "pageSize": limit,
        "presaleType": "stock",
        "searchType": 2,
        "keyword": keyword,
        "componentLibraryType": _LIBRARY_TYPE_MAP.get(library_type),
        "stockFlag": in_stock,
        "stockSort": None,
        "firstSortName": category,
        "secondSortName": subcategory,
        "componentBrandList": brands or [],
        "searchSource": "search",
        "componentSpecificationList": packages or [],
        "componentAttributeList": attributes or [],
        "paramList": [],
        "startStockNumber": min_stock,
        "endStockNumber": max_stock,
    }

    result = client.api_post(_CATALOG_SEARCH_PATH, payload)
    page_info = (result.get("data") or {}).get("componentPageInfo") or {}
    items = page_info.get("list") or []

    return {
        "pagination": {
            "page": page_info.get("currentPage", page),
            "pageSize": page_info.get("pageSize", limit),
            "total": page_info.get("total", 0),
        },
        "components": [_extract_catalog_component(c) for c in items],
    }


def _extract_catalog_component(comp: dict) -> dict:
    lib_raw = comp.get("componentLibraryType")
    lib_label = {"base": "basic", "expand": "extended"}.get(lib_raw, lib_raw)

    prices_raw = comp.get("componentPrices") or comp.get("priceList") or []
    prices = [
        {
            "minQty": p.get("startNumber"),
            "maxQty": p.get("endNumber"),
            "unitPrice": p.get("productPrice"),
        }
        for p in prices_raw
    ]

    attrs_raw = comp.get("attributes") or []
    attrs = {}
    for a in attrs_raw:
        name = a.get("attribute_name_en") or a.get("attributeName")
        val = a.get("attribute_value_name") or a.get("attributeValue")
        if name:
            attrs[name] = val

    return {
        "lcscPart": comp.get("componentCode"),
        "mfrPart": comp.get("componentModelEn") or comp.get("componentModel"),
        "manufacturer": comp.get("componentBrandEn") or comp.get("componentBrand"),
        "category": comp.get("firstSortName"),
        "subcategory": comp.get("secondSortName"),
        "package": comp.get("componentSpecificationEn") or comp.get("componentSpecification"),
        "description": comp.get("describe") or comp.get("description"),
        "libraryType": lib_label,
        "stock": comp.get("stockCount"),
        "minOrderQty": comp.get("minPurchaseNum"),
        "prices": prices,
        "attributes": attrs,
        "datasheetUrl": comp.get("dataManualUrl"),
    }
