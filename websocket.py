"""Websocket API used by the Home Budget sidebar panel."""
import base64
import zipfile
from xml.etree import ElementTree

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .categorizer import UNSORTED
from .const import CONF_CATEGORIES, DEFAULT_CATEGORIES, DOMAIN, KINDS
from .revolut import parse_revolut

TX_FIELDS = {
    vol.Required("amount"): vol.Coerce(float),
    vol.Required("kind"): vol.In(KINDS),
    vol.Required("category"): str,
    vol.Required("date"): str,
    vol.Optional("description", default=""): str,
    vol.Optional("account", default=""): str,
    vol.Optional("currency"): str,
}


def _context(hass: HomeAssistant):
    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, dict) and "store" in value:
            return value
    return None


async def _refresh(ctx):
    coordinator = ctx.get("coordinator")
    if coordinator:
        await coordinator.async_request_refresh()


def _categories(ctx):
    cats = list(ctx["entry"].options.get(CONF_CATEGORIES, DEFAULT_CATEGORIES))
    return cats if UNSORTED in cats else cats + [UNSORTED]


def _with_context(func):
    async def wrapper(hass, connection, msg):
        ctx = _context(hass)
        if ctx is None:
            connection.send_error(msg["id"], "not_loaded", "Home Budget is not loaded")
            return
        try:
            await func(hass, connection, msg, ctx)
        except ValueError as err:
            connection.send_error(msg["id"], "invalid_data", str(err))
    return wrapper


@websocket_api.websocket_command({vol.Required("type"): "home_budget/info"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_info(hass, connection, msg, ctx):
    connection.send_result(msg["id"], {
        "currency": ctx["currency"], "categories": _categories(ctx), "unsorted": UNSORTED,
    })


@websocket_api.websocket_command({
    vol.Required("type"): "home_budget/list",
    vol.Optional("month"): str,
    vol.Optional("category"): str,
    vol.Optional("kind"): str,
    vol.Optional("search"): str,
    vol.Optional("limit", default=100): vol.All(int, vol.Range(min=1, max=500)),
    vol.Optional("offset", default=0): vol.All(int, vol.Range(min=0)),
})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_list(hass, connection, msg, ctx):
    result = await ctx["store"].async_list(
        currency=ctx["currency"], month=msg.get("month") or None,
        category=msg.get("category") or None, kind=msg.get("kind") or None,
        search=msg.get("search") or None, limit=msg["limit"], offset=msg["offset"],
    )
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "home_budget/stats",
    vol.Required("year"): vol.All(int, vol.Range(min=1970, max=2200)),
    vol.Optional("month", default=0): vol.All(int, vol.Range(min=0, max=12)),
    vol.Optional("exclude_transfers", default=False): bool,
})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_stats(hass, connection, msg, ctx):
    result = await ctx["store"].async_stats(
        ctx["currency"], msg["year"], msg["month"], msg["exclude_transfers"]
    )
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "home_budget/add", **TX_FIELDS})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_add(hass, connection, msg, ctx):
    result = await ctx["store"].async_add(
        amount=msg["amount"], currency=msg.get("currency") or ctx["currency"], kind=msg["kind"],
        category=msg["category"], tx_date=msg["date"], description=msg["description"],
        account=msg["account"],
    )
    hass.bus.async_fire(f"{DOMAIN}_transaction_added", result)
    await _refresh(ctx)
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "home_budget/update",
    vol.Required("transaction_id"): int,
    **TX_FIELDS,
})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_update(hass, connection, msg, ctx):
    updated = await ctx["store"].async_update(
        msg["transaction_id"], amount=msg["amount"], currency=msg.get("currency") or ctx["currency"],
        kind=msg["kind"], category=msg["category"], tx_date=msg["date"],
        description=msg["description"], account=msg["account"],
    )
    if not updated:
        connection.send_error(msg["id"], "not_found", "Transaction not found")
        return
    await _refresh(ctx)
    connection.send_result(msg["id"], {"updated": True})


@websocket_api.websocket_command({
    vol.Required("type"): "home_budget/delete",
    vol.Required("transaction_id"): int,
})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_delete(hass, connection, msg, ctx):
    if not await ctx["store"].async_delete(msg["transaction_id"]):
        connection.send_error(msg["id"], "not_found", "Transaction not found")
        return
    await _refresh(ctx)
    connection.send_result(msg["id"], {"deleted": True})


@websocket_api.websocket_command({
    vol.Required("type"): "home_budget/recategorize",
    vol.Required("from_category"): str,
    vol.Required("to_category"): str,
    vol.Required("description"): str,
    vol.Optional("remember", default=False): bool,
})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_recategorize(hass, connection, msg, ctx):
    count = await ctx["store"].async_recategorize(
        from_category=msg["from_category"], to_category=msg["to_category"],
        description=msg["description"], remember=msg["remember"],
    )
    await _refresh(ctx)
    connection.send_result(msg["id"], {"updated": count})


@websocket_api.websocket_command({vol.Required("type"): "home_budget/rules"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_rules(hass, connection, msg, ctx):
    connection.send_result(msg["id"], {"rules": await ctx["store"].async_rules()})


@websocket_api.websocket_command({
    vol.Required("type"): "home_budget/add_rule",
    vol.Required("pattern"): str,
    vol.Required("category"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_add_rule(hass, connection, msg, ctx):
    applied = await ctx["store"].async_add_rule(msg["pattern"], msg["category"])
    await _refresh(ctx)
    connection.send_result(msg["id"], {"applied": applied})


@websocket_api.websocket_command({
    vol.Required("type"): "home_budget/delete_rule",
    vol.Required("rule_id"): int,
})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_delete_rule(hass, connection, msg, ctx):
    if not await ctx["store"].async_delete_rule(msg["rule_id"]):
        connection.send_error(msg["id"], "not_found", "Rule not found")
        return
    connection.send_result(msg["id"], {"deleted": True})


@websocket_api.websocket_command({
    vol.Required("type"): "home_budget/import",
    vol.Required("content"): str,
    vol.Optional("skip_transfers", default=False): bool,
})
@websocket_api.require_admin
@websocket_api.async_response
@_with_context
async def ws_import(hass, connection, msg, ctx):
    try:
        rules = [(r["pattern"], r["category"]) for r in await ctx["store"].async_rules()]
        content = base64.b64decode(msg["content"], validate=True)
        transactions, skipped, parse_errors = await hass.async_add_executor_job(
            parse_revolut, content, msg["skip_transfers"], rules
        )
    except (ValueError, zipfile.BadZipFile, ElementTree.ParseError) as err:
        connection.send_error(msg["id"], "invalid_file", str(err))
        return
    result = await ctx["store"].async_import(transactions)
    await _refresh(ctx)
    connection.send_result(msg["id"], {
        "inserted": result["inserted"], "duplicates": result["duplicates"],
        "skipped": skipped, "errors": parse_errors + result["errors"],
    })


def async_register_websocket_api(hass: HomeAssistant):
    for command in (ws_info, ws_stats, ws_list, ws_add, ws_update, ws_delete, ws_recategorize, ws_import,
                    ws_rules, ws_add_rule, ws_delete_rule):
        websocket_api.async_register_command(hass, command)
