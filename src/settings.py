# Standard library imports.
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
# Related third party imports.
import yaml
# Local application/library specific imports.
from constants.general_settings import YAML_SETTINGS


@dataclass(frozen=True)
class YamlSettings:
    domain: str | None = 'atmosphere'
    start: str | None = '01/01/2020'
    end: str | None = '31/12/2020'
    group: str | None = 'M'
    title_period: str | None = '2020'
    side_title_period: str | None = '2020'
    using_cache: bool = 'True'
    cache_path: str = 'cache'
    # file_name_period: str | None = 'todo'
    # output_dir: str = 'output'
    # version_output: bool = True


class Settings:

    def __init__(self) -> None:
        self.settings = self.read_settings()
        self.init_files()
        return

    @staticmethod
    def read_settings() -> YamlSettings:
        try:
            with open(YAML_SETTINGS, 'r') as yaml_handler:
                data = YamlSettings(**yaml.safe_load(yaml_handler))
        except FileNotFoundError:
            return YamlSettings()
        else:
            return data


    def init_files(self) -> None:
        cache_file = Path(self.settings.cache_path)
        # Create the cache directory if it doesn't exist.
        Path(cache_file.parents[0]).mkdir(parents=True, exist_ok=True)
        return
