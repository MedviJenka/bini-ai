import warnings
from functools import cached_property
from dataclasses import dataclass, field
from logfire import Logfire, configure

from backend.settings import Config

warnings.filterwarnings('ignore')


@dataclass
class Logger:

    name: str
    _logger: object = field(init=False, default=None)

    @cached_property
    def fire(self) -> Logfire:
        try:
            return configure(service_name=self.name, token=Config.LOGFIRE_TOKEN)
        except Exception:
            return configure(service_name=self.name, send_to_logfire=False)
