import logging
import os
import json
from datetime import datetime, timedelta
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_ZIPCODE,
    CONF_MUNICIPALITY,
    CONF_PARISH,
)

_LOGGER = logging.getLogger(__name__)

MUNICIPALITIES_API_URL = "https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/municipalities-portugal/exports/json"
PARISHES_API_URL = "https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/civil-parishes-portugal/exports/json"
PARISHES_ALT_API_URL = "https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/civil-parishes-portugal-v2/exports/json"

CACHE_FILE_NAME = "parishes_cache.json"
CACHE_MAX_AGE_DAYS = 30

class ERedesCortesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow para a integração E-Redes Interrupções."""

    VERSION = 1

    async def _async_get_options_from_api(self, url, preferred_keys, alt_url=None):
        """Busca e extrai nomes válidos a partir dos exports, ignorando códigos e IDs numéricos."""
        options = []
        urls_to_try = [url]
        if alt_url:
            urls_to_try.append(alt_url)

        session = async_get_clientsession(self.hass)

        for target_url in urls_to_try:
            try:
                async with session.get(target_url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data if isinstance(data, list) else data.get("results", data.get("records", []))
                        
                        for record in records:
                            if not isinstance(record, dict):
                                continue
                            
                            val = None
                            for key in preferred_keys:
                                if key in record and record[key]:
                                    val = record[key]
                                    break
                            
                            if not val:
                                for k, v in record.items():
                                    k_lower = k.lower()
                                    if any(bad in k_lower for bad in ['code', 'cod', 'id', 'object', 'lat', 'lon', 'geom', 'shape', 'url']):
                                        continue
                                    if any(good in k_lower for good in ['name', 'nome', 'con', 'fre']):
                                        if v and isinstance(v, str) and not v.isdigit():
                                            val = v
                                            break
                            
                            if val:
                                val_str = str(val).strip()
                                if val_str and not val_str.isdigit():
                                    options.append(val_str)
                        
                        if options:
                            break
                    else:
                        _LOGGER.warning("E-Redes API Export HTTP %s em %s", response.status, target_url)
            except Exception as err:
                _LOGGER.error("Erro ao contactar API Export em %s: %s", target_url, err)
        
        return sorted(list(set(options)))

    async def _async_get_municipalities(self):
        return await self._async_get_options_from_api(MUNICIPALITIES_API_URL, ["con_name", "municipality", "concelho", "nome", "name"])

    async def _async_get_parishes(self):
        """Obtém as freguesias com recurso a cache local de 30 dias para evitar downloads massivos constantes."""
        cache_path = os.path.join(os.path.dirname(__file__), CACHE_FILE_NAME)
        max_age = timedelta(days=CACHE_MAX_AGE_DAYS)

        # 1. Tentar ler do cache local se for válido e recente (< 30 dias)
        if os.path.exists(cache_path):
            try:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
                if datetime.now() - file_mtime < max_age:
                    def _load_cache():
                        with open(cache_path, "r", encoding="utf-8") as f:
                            return json.load(f)
                    
                    cached_options = await self.hass.async_add_executor_job(_load_cache)
                    if cached_options:
                        _LOGGER.debug("A carregar lista de freguesias a partir do cache local.")
                        return cached_options
            except Exception as err:
                _LOGGER.warning("Erro ao ler cache local de freguesias: %s", err)

        # 2. Se o cache não existir ou estiver expirado, ir buscar à API
        _LOGGER.info("A descarregar lista completa de freguesias da API da E-Redes...")
        options = await self._async_get_options_from_api(PARISHES_API_URL, ["fre_name", "parish", "freguesia", "nome", "name"], PARISHES_ALT_API_URL)

        # 3. Guardar no cache local se obteve resultados
        if options:
            try:
                def _save_cache():
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(options, f, ensure_ascii=False, indent=2)
                
                await self.hass.async_add_executor_job(_save_cache)
                _LOGGER.info("Cache de freguesias atualizado com sucesso (%d registos).", len(options))
            except Exception as err:
                _LOGGER.error("Erro ao escrever cache local de freguesias: %s", err)

        return options

    async def async_step_user(self, user_input=None):
        """Passo inicial de configuração pelo utilizador."""
        errors = {}

        if user_input is not None:
            if not any(user_input.values()):
                errors["base"] = "no_fields_provided"
            else:
                title_parts = [v for k, v in user_input.items() if v]
                title_text = " - ".join(title_parts)
                
                return self.async_create_entry(
                    title=f"E-Redes ({title_text})",
                    data=user_input
                )

        municipality_options = await self._async_get_municipalities()
        parish_options = await self._async_get_parishes()

        schema = vol.Schema({
            vol.Optional(CONF_MUNICIPALITY): selector({
                "select": {
                    "options": municipality_options,
                    "mode": "dropdown",
                }
            }),
            vol.Optional(CONF_PARISH): selector({
                "select": {
                    "options": parish_options,
                    "mode": "dropdown",
                }
            }),
            vol.Optional(CONF_ZIPCODE): cv.string,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )