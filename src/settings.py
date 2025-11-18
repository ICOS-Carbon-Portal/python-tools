# Standard library imports.
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
# Related third party imports.
import yaml
# Local application/library specific imports.
from src.constants.general_settings import YAML_SETTINGS


@dataclass(frozen=True)
class YamlSettings:
    cache_path: str
    domain: str | None = 'atmosphere'
    start: str | None = '01/01/2020'
    end: str | None = '31/12/2020'
    group: str | None = 'M'
    title_period: str | None = '2020'
    side_title_period: str | None = '2020'
    using_cache: bool = 'True'
    cache_path: str | Path = Path('cache')
    file_name_period: str | None = 'todo'
    output_dir: str = 'output'


class Settings:

    def __init__(self) -> None:
        self.settings = self.read_settings()
        self.init_files()
        return

    @staticmethod
    def read_settings() -> YamlSettings:
        with open(YAML_SETTINGS, 'r') as yaml_handler:
            data = YamlSettings(**yaml.safe_load(yaml_handler))
        return data

    def init_files(self) -> None:
        Path(self.settings.output_dir).mkdir(parents=True, exist_ok=True)
        return
