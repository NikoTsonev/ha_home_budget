from datetime import date
import zipfile
from xml.etree import ElementTree

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.core import callback
from homeassistant.helpers import selector

from .categorizer import UNSORTED
from .const import CONF_CATEGORIES, CONF_CURRENCY, DEFAULT_CATEGORIES, DEFAULT_CURRENCY, DOMAIN, KINDS
from .revolut import parse_revolut

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
        return HomeBudgetOptionsFlow()

def _clean_categories(values):
    seen, result = set(), []
    for value in values:
        name = str(value).strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result

class HomeBudgetOptionsFlow(config_entries.OptionsFlow):
    """Options flow; requires Home Assistant 2024.12+ (config_entry provided by base)."""

    def _data(self):
        return self.hass.data[DOMAIN][self.config_entry.entry_id]

    def _currency(self):
        return self.config_entry.options.get(
            CONF_CURRENCY, self.config_entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY)
        )

    def _categories(self):
        cats = list(self.config_entry.options.get(CONF_CATEGORIES, DEFAULT_CATEGORIES))
        return cats if UNSORTED in cats else cats + [UNSORTED]

    @staticmethod
    def _category_selector(options, multiple=False):
        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options, multiple=multiple, custom_value=True,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

    async def _refresh(self):
        coordinator = self._data().get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_transaction", "import_revolut", "review_unsorted", "settings"],
        )

    async def async_step_add_transaction(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                result = await self._data()["store"].async_add(
                    amount=user_input["amount"],
                    currency=user_input.get(CONF_CURRENCY) or self._currency(),
                    kind=user_input["kind"],
                    category=user_input["category"],
                    tx_date=user_input.get("date"),
                    description=user_input.get("description", ""),
                    account=user_input.get("account", ""),
                )
            except ValueError as err:
                errors["base"] = "invalid_transaction"
                self._error = str(err)
            else:
                self.hass.bus.async_fire(f"{DOMAIN}_transaction_added", result)
                await self._refresh()
                return self.async_abort(reason="transaction_added")

        schema = vol.Schema({
            vol.Required("kind", default="expense"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=KINDS, translation_key="kind",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required("amount"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, step=0.01, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required("category"): self._category_selector(self._categories()),
            vol.Optional("date", default=date.today().isoformat()): selector.DateSelector(),
            vol.Optional("description"): str,
            vol.Optional("account"): str,
            vol.Optional(CONF_CURRENCY, default=self._currency()): str,
        })
        return self.async_show_form(
            step_id="add_transaction", data_schema=schema, errors=errors,
            description_placeholders={"error": getattr(self, "_error", "")},
        )

    async def async_step_import_revolut(self, user_input=None):
        errors = {}
        placeholders = {"details": ""}
        if user_input is not None:
            try:
                content = await self.hass.async_add_executor_job(
                    self._read_upload, user_input["file"]
                )
                rules = [
                    (r["pattern"], r["category"])
                    for r in await self._data()["store"].async_rules()
                ]
                transactions, skipped, parse_errors = parse_revolut(
                    content, user_input["skip_transfers"], rules
                )
            except (ValueError, OSError, zipfile.BadZipFile, ElementTree.ParseError) as err:
                errors["base"] = "invalid_csv"
                placeholders["details"] = str(err)
            else:
                result = await self._data()["store"].async_import(transactions)
                await self._refresh()
                problems = parse_errors + result["errors"]
                unsorted = await self._data()["store"].async_unsorted_groups(UNSORTED)
                self._import_summary = {
                    "inserted": str(result["inserted"]),
                    "duplicates": str(result["duplicates"]),
                    "skipped": str(skipped),
                    "errors": str(len(problems)),
                    "unsorted": str(sum(g["n"] for g in unsorted)),
                }
                return await self.async_step_import_done()

        schema = vol.Schema({
            vol.Required("file"): selector.FileSelector(
                selector.FileSelectorConfig(accept=".csv,.xlsx,text/csv")
            ),
            vol.Required("skip_transfers", default=False): bool,
        })
        return self.async_show_form(
            step_id="import_revolut", data_schema=schema, errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_import_done(self, user_input=None):
        return self.async_show_menu(
            step_id="import_done",
            menu_options=["review_unsorted", "finish"],
            description_placeholders=self._import_summary,
        )

    async def async_step_finish(self, user_input=None):
        return self.async_abort(reason="import_done", description_placeholders=self._import_summary)

    async def async_step_review_unsorted(self, user_input=None):
        store = self._data()["store"]
        if user_input is not None:
            current = self._review_current
            if user_input.get("category"):
                await store.async_recategorize(
                    from_category=UNSORTED, to_category=user_input["category"],
                    description=current["description"], remember=True,
                )
                await self._refresh()
            # An empty selection skips this group; remember it so the loop moves on.
            self._review_skipped.add((current["description"], current["kind"]))
        else:
            self._review_skipped = set()

        groups = [
            g for g in await store.async_unsorted_groups(UNSORTED)
            if (g["description"], g["kind"]) not in self._review_skipped
        ]
        if not groups:
            return self.async_abort(reason="review_done")
        self._review_current = groups[0]
        current = groups[0]
        schema = vol.Schema({
            vol.Optional("category"): self._category_selector(
                [c for c in self._categories() if c != UNSORTED]
            ),
        })
        return self.async_show_form(
            step_id="review_unsorted", data_schema=schema,
            description_placeholders={
                "description": current["description"] or "(no description)",
                "kind": current["kind"],
                "count": str(current["n"]),
                "total": f"{current['total']:.2f} {current['currency']}",
                "remaining": str(len(groups)),
            },
        )

    def _read_upload(self, file_id):
        with process_uploaded_file(self.hass, file_id) as path:
            return path.read_bytes()

    async def async_step_settings(self, user_input=None):
        errors = {}
        categories = self._categories()
        if user_input is not None:
            currency = user_input[CONF_CURRENCY].upper().strip()
            categories = _clean_categories(user_input.get(CONF_CATEGORIES, []))
            if len(currency) != 3 or not currency.isalpha():
                errors["base"] = "invalid_currency"
            elif not categories:
                errors["base"] = "no_categories"
            else:
                return self.async_create_entry(
                    title="",
                    data={CONF_CURRENCY: currency, CONF_CATEGORIES: categories},
                )
        schema = vol.Schema({
            vol.Required(CONF_CURRENCY, default=self._currency()): str,
            vol.Required(CONF_CATEGORIES, default=categories): self._category_selector(
                categories, multiple=True
            ),
        })
        return self.async_show_form(step_id="settings", data_schema=schema, errors=errors)

