"""Config flow for the Nature Remo integration."""

from collections.abc import Mapping
from typing import Any

import probatio
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
from homeassistant.helpers.update_coordinator import UpdateFailed

from . import (
    CONF_COOL_TEMP,
    CONF_HEAT_TEMP,
    DEFAULT_COOL_TEMP,
    DEFAULT_HEAT_TEMP,
    DOMAIN,
    NatureRemoAPI,
)


class NatureRemoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nature Remo."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._validate_input(user_input)
            if not errors:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Nature Remo", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(user_input),
            errors=errors,
        )

    async def async_step_import(self, import_input: dict[str, Any]) -> ConfigFlowResult:
        """Import a YAML configuration."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors = await self._validate_input(import_input)
        if errors:
            return self.async_abort(reason=next(iter(errors.values())))

        return self.async_create_entry(title="Nature Remo", data=import_input)

    async def async_step_reauth(self, _entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start reauthentication after Nature Remo rejects the token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new access token and reload the entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await self._validate_input(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self._schema(user_input),
            errors=errors,
        )

    async def _validate_input(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate the user input allows us to connect."""
        session = async_get_clientsession(self.hass)
        api = NatureRemoAPI(user_input[CONF_ACCESS_TOKEN], session)
        try:
            await api.get()
        except ConfigEntryAuthFailed, UpdateFailed:
            return {"base": "cannot_connect"}
        except Exception:  # noqa: BLE001 - unknown failures stay on the form
            return {"base": "unknown"}
        return {}

    def _schema(self, user_input: dict[str, Any] | None = None) -> probatio.Schema:
        """Return the config flow schema."""
        user_input = user_input or {}
        return probatio.Schema(
            {
                probatio.Required(CONF_ACCESS_TOKEN): str,
                probatio.Optional(
                    CONF_COOL_TEMP,
                    default=user_input.get(CONF_COOL_TEMP, DEFAULT_COOL_TEMP),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=16,
                        max=30,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                probatio.Optional(
                    CONF_HEAT_TEMP,
                    default=user_input.get(CONF_HEAT_TEMP, DEFAULT_HEAT_TEMP),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=16,
                        max=30,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )
