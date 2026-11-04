import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_change

from .const import (
    ATTR_ACCOUNT, ATTR_AMOUNT, ATTR_CATEGORY, ATTR_DATE, ATTR_DESCRIPTION,
    ATTR_EXTERNAL_ID, ATTR_KIND, ATTR_TRANSACTION_ID, CONF_CURRENCY, DEFAULT_CURRENCY,
    DOMAIN, PLATFORMS, SERVICE_ADD_TRANSACTION, SERVICE_DELETE_TRANSACTION, SERVICE_REFRESH,
)
from .panel import async_register_panel, async_unregister_panel
from .storage import BudgetStore
from .websocket import async_register_websocket_api

ADD_SCHEMA = vol.Schema({
    vol.Required(ATTR_AMOUNT): vol.Coerce(float),
    vol.Required(ATTR_KIND): vol.In(["expense", "income"]),
    vol.Required(ATTR_CATEGORY): str,
    vol.Optional(ATTR_DATE): str,
    vol.Optional(ATTR_DESCRIPTION, default=""): str,
    vol.Optional(ATTR_ACCOUNT, default=""): str,
    vol.Optional("currency"): str,
    vol.Optional("source", default="manual"): str,
    vol.Optional(ATTR_EXTERNAL_ID): str,
})
DELETE_SCHEMA = vol.Schema({vol.Required(ATTR_TRANSACTION_ID): vol.Coerce(int)})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    currency = entry.options.get(CONF_CURRENCY, entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY))
    store = BudgetStore(hass)
    await store.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "store": store, "currency": currency, "entry": entry,
    }

    async def refresh_entities():
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()

    async def add_transaction(call: ServiceCall):
        data = call.data
        user_id = call.context.user_id or ""
        user = await hass.auth.async_get_user(user_id) if user_id else None
        try:
            result = await store.async_add(
                created_by=(user.name if user else "") or "",
                created_by_id=user_id,
                amount=data[ATTR_AMOUNT],
                currency=data.get("currency", currency),
                kind=data[ATTR_KIND],
                category=data[ATTR_CATEGORY],
                tx_date=data.get(ATTR_DATE),
                description=data.get(ATTR_DESCRIPTION, ""),
                account=data.get(ATTR_ACCOUNT, ""),
                source=data.get("source", "manual"),
                external_id=data.get(ATTR_EXTERNAL_ID),
            )
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        hass.bus.async_fire(f"{DOMAIN}_transaction_added", result)
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()

    async def delete_transaction(call: ServiceCall):
        deleted = await store.async_delete(call.data[ATTR_TRANSACTION_ID])
        if not deleted:
            raise HomeAssistantError("Transaction ID not found")
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_ADD_TRANSACTION, add_transaction, schema=ADD_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_TRANSACTION, delete_transaction, schema=DELETE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REFRESH, refresh_entities)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_websocket_api(hass)
    await async_register_panel(hass)

    async def process_recurring(_now=None):
        if await store.async_process_recurring():
            await refresh_entities()

    await process_recurring()
    entry.async_on_unload(async_track_time_change(hass, process_recurring, hour=0, minute=10, second=0))
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True

async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_unregister_panel(hass)
    for service in (SERVICE_ADD_TRANSACTION, SERVICE_DELETE_TRANSACTION, SERVICE_REFRESH):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
