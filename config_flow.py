import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_CURRENCY, DEFAULT_CURRENCY, DOMAIN

class HomeBudgetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            currency = user_input[CONF_CURRENCY].upper().strip()
            if len(currency) != 3 or not currency.isalpha():
                errors["base"] = "invalid_currency"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Home Budget",
                    data={CONF_CURRENCY: currency},
                )

        schema = vol.Schema({
            vol.Required(CONF_CURRENCY, default=DEFAULT_CURRENCY): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HomeBudgetOptionsFlow(config_entry)

class HomeBudgetOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            currency = user_input[CONF_CURRENCY].upper().strip()
            if len(currency) == 3 and currency.isalpha():
                return self.async_create_entry(title="", data={CONF_CURRENCY: currency})
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({vol.Required(CONF_CURRENCY, default="EUR"): str}),
                errors={"base": "invalid_currency"},
            )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_CURRENCY,
                    default=self.config_entry.options.get(
                        CONF_CURRENCY, self.config_entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY)
                    ),
                ): str,
            }),
        )
