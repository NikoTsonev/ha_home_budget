from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from datetime import timedelta

from .const import CONF_CURRENCY, DEFAULT_CURRENCY, DOMAIN
from .storage import BudgetStore

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    data = hass.data[DOMAIN][entry.entry_id]
    store: BudgetStore = data["store"]
    currency = entry.options.get(CONF_CURRENCY, entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY))

    async def async_update_data():
        return await store.async_summary(currency)

    coordinator = DataUpdateCoordinator(
        hass, logger=__import__("logging").getLogger(__name__),
        name="Home Budget", update_method=async_update_data,
        update_interval=timedelta(minutes=5),
    )
    await coordinator.async_config_entry_first_refresh()
    data["coordinator"] = coordinator
    async_add_entities([
        BudgetSensor(coordinator, currency, "expenses", "Monthly expenses", "mdi:cash-minus"),
        BudgetSensor(coordinator, currency, "income", "Monthly income", "mdi:cash-plus"),
        BudgetSensor(coordinator, currency, "balance", "Monthly balance", "mdi:scale-balance"),
        BudgetSensor(coordinator, currency, "transaction_count", "Monthly transactions", "mdi:receipt-text", unit=None),
    ])

class BudgetSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, currency, key, name, icon, unit="currency"):
        super().__init__(coordinator)
        self.key = key
        self.currency = currency
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"home_budget_{key}"
        if unit == "currency":
            self._attr_native_unit_of_measurement = currency
            self._attr_suggested_display_precision = 2
        elif unit is None:
            self._attr_native_unit_of_measurement = None

    @property
    def native_value(self):
        return self.coordinator.data.get(self.key)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "month": data.get("month"),
            "expenses_by_category": data.get("categories", {}),
            "recent_transactions": data.get("recent", []),
        }
