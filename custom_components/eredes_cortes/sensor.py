import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurar sensores da E-Redes a partir de uma config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ERedesCortesSensor(coordinator, entry)])

class ERedesCortesSensor(CoordinatorEntity, SensorEntity):
    """Sensor para monitorizar interrupções de energia da E-Redes."""

    def __init__(self, coordinator, entry) -> None:
        """Inicializar o sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_interrupcoes"
        self._attr_name = f"E-Redes Interrupções ({entry.title})"

    @property
    def native_value(self):
        """Retorna o número total de interrupções ativas/agendadas."""
        if self.coordinator.data:
            return self.coordinator.data.get("count", 0)
        return 0

    @property
    def icon(self):
        """Ícone dinâmico com base no número de interrupções."""
        return "mdi:flash-alert" if self.native_value > 0 else "mdi:flash-check"

    @property
    def extra_state_attributes(self):
        """Atributos detalhados limitados para respeitar o limite de 16KB do Recorder."""
        if not self.coordinator.data:
            return {}
        
        interrupcoes = self.coordinator.data.get("interrupcoes", [])
        
        return {
            "total_interrupcoes": len(interrupcoes),
            "interrupcoes": interrupcoes[:10],  # Limitado aos primeiros 10 registos para evitar o erro de tamanho
            "filtro_aplicado": self.coordinator.data.get("filter_info", ""),
        }