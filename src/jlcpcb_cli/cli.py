"""CLI entry point for jlcpcb-cli."""

import json
import sys

import click

from jlcpcb_cli.core.web_client import get_web_client
from jlcpcb_cli.core.billing import list_billing, get_billing_detail, get_billing_invoice
from jlcpcb_cli.core.orders import get_order
from jlcpcb_cli.core.parts import list_inventory, parse_attr_filters, search_catalog
from jlcpcb_cli.core.smt import get_bom, get_usage
from jlcpcb_cli.core.web_orders import list_orders
from jlcpcb_cli.core.web_parts import list_parts_orders, get_parts_order
from jlcpcb_cli.core import auth


def _output(data) -> None:
    click.echo(json.dumps(data, indent=2, default=str))


@click.group()
@click.option("--json", "json_output", is_flag=True, hidden=True)
def cli(json_output):
    """JLCPCB order data CLI."""
    pass


@cli.command()
def login():
    """Login to JLCPCB via browser."""
    auth.login()


@cli.group()
def orders():
    """PCB/SMT order operations."""
    pass


@orders.command("list")
@click.option(
    "--status",
    type=click.Choice(["all", "shipped", "production", "cancelled", "unpaid", "review"]),
    default="all",
    help="Filter by order status.",
)
@click.option("--search", default=None, help="Search by keyword.")
@click.option("--limit", default=15, type=int, help="Results per page.")
@click.option("--page", default=1, type=int, help="Page number.")
def orders_list(status, search, limit, page):
    """List order batches."""
    try:
        result = list_orders(
            get_web_client(), status=status, search=search, limit=limit, page=page
        )
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@orders.command("get")
@click.argument("batch_num")
def orders_get(batch_num):
    """Get full details for an order batch."""
    try:
        result = get_order(get_web_client(), batch_num)
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@orders.command("bom")
@click.argument("batch_num")
def orders_bom(batch_num):
    """Get the per-component BOM of a batch's SMT orders."""
    try:
        result = get_bom(get_web_client(), batch_num)
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@orders.command("usage")
@click.argument("batch_num")
def orders_usage(batch_num):
    """Get the Parts Manager stock a batch's SMT orders consumed."""
    try:
        result = get_usage(get_web_client(), batch_num)
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def parts():
    """Parts Manager: catalog search, inventory, and order history."""
    pass


@parts.command("search")
@click.argument("keyword", default="")
@click.option(
    "--library-type",
    type=click.Choice(["all", "basic", "extended"]),
    default="all",
    help="Filter by Basic or Extended library type.",
)
@click.option("--in-stock", is_flag=True, help="Only show parts currently in stock.")
@click.option("--min-stock", default=None, type=int, help="Minimum stock count.")
@click.option("--max-stock", default=None, type=int, help="Maximum stock count.")
@click.option("--category", default=None, help="Primary category (e.g. Resistors).")
@click.option(
    "--subcategory",
    default=None,
    help="Subcategory (e.g. 'Chip Resistor - Surface Mount').",
)
@click.option("--package", "packages", multiple=True, help="Filter by package/footprint (repeatable).")
@click.option("--brand", "brands", multiple=True, help="Filter by manufacturer/brand (repeatable).")
@click.option(
    "--attr",
    "attrs",
    multiple=True,
    help="Filter by attribute as 'Key=Value' (repeatable, e.g. 'Resistance=10kΩ').",
)
@click.option("--limit", default=25, type=int, help="Results per page.")
@click.option("--page", default=1, type=int, help="Page number.")
def parts_search(
    keyword,
    library_type,
    in_stock,
    min_stock,
    max_stock,
    category,
    subcategory,
    packages,
    brands,
    attrs,
    limit,
    page,
):
    """Search JLCPCB's SMT parts catalog by part number, keyword, or attributes."""
    try:
        parsed_attrs = parse_attr_filters(attrs) if attrs else None
        result = search_catalog(
            get_web_client(),
            keyword=keyword,
            page=page,
            limit=limit,
            library_type=library_type,
            in_stock=in_stock,
            min_stock=min_stock,
            max_stock=max_stock,
            category=category,
            subcategory=subcategory,
            packages=list(packages) if packages else None,
            brands=list(brands) if brands else None,
            attributes=parsed_attrs,
        )
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@parts.command("inventory")
@click.option("--search", default="", help="Search by keyword.")
@click.option("--limit", default=30, type=int, help="Results per page.")
@click.option("--page", default=1, type=int, help="Page number.")
def parts_inventory(search, limit, page):
    """List components stored at JLCPCB."""
    try:
        result = list_inventory(
            get_web_client(), search=search, page=page, limit=limit
        )
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@parts.command("list-orders")
@click.option(
    "--status",
    type=click.Choice(["all", "in_progress", "unpaid", "cancelled", "completed"]),
    default="all",
    help="Filter by order status.",
)
@click.option("--search", default=None, help="Search by keyword.")
@click.option("--limit", default=25, type=int, help="Results per page.")
@click.option("--page", default=1, type=int, help="Page number.")
def parts_list_orders(status, search, limit, page):
    """List parts purchase order batches."""
    try:
        result = list_parts_orders(
            get_web_client(), status=status, search=search, limit=limit, page=page
        )
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@parts.command("get-order")
@click.argument("batch_no")
def parts_get_order(batch_no):
    """Get full details for a parts order batch."""
    try:
        result = get_parts_order(get_web_client(), batch_no)
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def billing():
    """Billing: payment history, receipts, and invoices."""
    pass


@billing.command("list")
@click.option("--search", default=None, help="Filter by batch number.")
@click.option("--limit", default=10, type=int, help="Results per page.")
@click.option("--page", default=1, type=int, help="Page number.")
def billing_list(search, limit, page):
    """List billing batch orders with payment summaries."""
    try:
        result = list_billing(
            get_web_client(), search=search, limit=limit, page=page
        )
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@billing.command("get")
@click.argument("batch_num")
@click.option("--download", "download_dir", default=None, help="Save each receipt/credit note JSON to directory.")
def billing_get(batch_num, download_dir):
    """Get full billing detail with transaction receipts for a batch."""
    try:
        result = get_billing_detail(
            get_web_client(), batch_num, download_dir=download_dir
        )
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@billing.command("invoice")
@click.argument("batch_num")
@click.option("--download", "download_dir", default=None, help="Save invoice JSON to directory.")
def billing_invoice(batch_num, download_dir):
    """Get invoice data for a billing batch."""
    try:
        result = get_billing_invoice(
            get_web_client(), batch_num, download_dir=download_dir
        )
        _output(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    cli()
