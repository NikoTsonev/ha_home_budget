"""Registers the Home Budget sidebar panel and its static frontend files."""
import os
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL = "home-budget"
PANEL_ELEMENT = "home-budget-panel"
STATIC_URL = "/home_budget_static"
_STATIC_KEY = f"{DOMAIN}_static_registered"


async def async_register_panel(hass: HomeAssistant):
    folder = Path(__file__).parent / "frontend"
    if not hass.data.get(_STATIC_KEY):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(folder), cache_headers=False)]
        )
        hass.data[_STATIC_KEY] = True
    version = int(os.path.getmtime(folder / "home-budget-panel.js"))
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_ELEMENT,
        frontend_url_path=PANEL_URL,
        module_url=f"{STATIC_URL}/home-budget-panel.js?v={version}",
        sidebar_title="Home Budget",
        sidebar_icon="mdi:wallet",
        require_admin=True,
    )


def async_unregister_panel(hass: HomeAssistant):
    frontend.async_remove_panel(hass, PANEL_URL)
