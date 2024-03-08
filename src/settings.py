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
    domain: str | None
    using_cache: bool
    cache_path: str
    start: str | None
    end: str | None
    group: str | None
    title_period: str | None
    side_title_period: str | None
    file_name_period: str | None
    output_dir: str
    version_output: bool


class Settings:

    def __init__(self) -> None:
        self.settings = self.read_settings()
        self.init_files()
        return

    @staticmethod
    def read_settings() -> YamlSettings:
        with open(YAML_SETTINGS, 'r') as yaml_handler:
            return YamlSettings(**yaml.safe_load(yaml_handler))

    def init_files(self) -> None:
        cache_file = Path(self.settings.cache_path)
        # Create the cache directory if it doesn't exist.
        Path(cache_file.parents[0]).mkdir(parents=True, exist_ok=True)
        return
