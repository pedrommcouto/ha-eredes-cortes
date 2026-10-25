import logging
from datetime import timedelta
import aiohttp

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_ZIPCODE,
    CONF_MUNICIPALITY,
    CONF_PARISH,
)

_LOGGER = logging.getLogger(__name__)

API_URL = "https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/network-scheduling-work/records"

class ERedesDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordenador para recolher dados de interrupções da E-Redes usando parâmetros refine."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Inicializar o coordenador."""
        self.entry = entry
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )

    async def _async_update_data(self):
        """Atualizar dados através do webservice da E-Redes utilizando múltiplos parâmetros refine."""
        try:
            session = async_get_clientsession(self.hass)
            
            municipality = self.entry.data.get(CONF_MUNICIPALITY)
            parish = self.entry.data.get(CONF_PARISH)
            zipcode = self.entry.data.get(CONF_ZIPCODE)

            # Usar lista de tuplos para permitir chaves 'refine' duplicadas no aiohttp
            params = [("limit", "100")]
            
            filters_applied = []
            if municipality:
                params.append(("refine", f"municipality:\"{municipality}\""))
                filters_applied.append(f"Concelho: {municipality}")
            if parish:
                params.append(("refine", f"parish:\"{parish}\""))
                filters_applied.append(f"Freguesia: {parish}")
            if zipcode:
                params.append(("refine", f"zipcode:\"{zipcode}\""))
                filters_applied.append(f"Código Postal: {zipcode}")

            async with session.get(API_URL, params=params, timeout=15) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Erro ao comunicar com a API da E-Redes: Código {response.status}")
                
                data = await response.json()
                results = data.get("results", [])

                interrupcoes = []
                for record in results:
                    interrupcoes.append({
                        "municipality": record.get("municipality"),
                        "parish": record.get("parish"),
                        "zipcode": record.get("zipcode"),
                        "data": record.get("data"),
                        "startdatetime": record.get("startdatetime"),
                        "enddatetime": record.get("enddatetime"),
                        "durationallocation": record.get("durationallocation"),
                    })

                return {
                    "count": len(interrupcoes),
                    "interrupcoes": interrupcoes,
                    "filter_info": " | ".join(filters_applied) if filters_applied else "Geral",
                }

        except Exception as err:
            raise UpdateFailed(f"Erro inesperado ao obter dados da E-Redes: {err}")

ERedesCortesDataUpdateCoordinator = ERedesDataUpdateCoordinator