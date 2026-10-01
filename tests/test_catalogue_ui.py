from pathlib import Path

from jinja2 import Environment
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "catalogue" / "pygeoapi-config.yml"
BASE_TEMPLATE = ROOT / "catalogue" / "templates" / "_base.html"
README_URL = "https://github.com/MeteoSwiss/wigos-portal-poc#readme"


def test_pygeoapi_uses_repository_template_override() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["server"]["templates"]["path"] == "catalogue/templates"


def test_pygeoapi_base_template_has_documentation_link() -> None:
    template = BASE_TEMPLATE.read_text(encoding="utf-8")
    assert f'href="{README_URL}"' in template
    assert ">Documentation</a>" in template


def test_pygeoapi_base_template_parses_as_jinja() -> None:
    template = BASE_TEMPLATE.read_text(encoding="utf-8")
    environment = Environment(extensions=["jinja2.ext.i18n"])
    environment.parse(template)
