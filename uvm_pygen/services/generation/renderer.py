"""Module for rendering templates using Jinja2."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from jinja2.environment import Template


class TemplateRenderer:
    """Handles Jinja2 environment and template rendering."""

    def __init__(self, template_dir: str | Path = "uvm_pygen/templates") -> None:
        """Initialize the Jinja2 environment with the specified template directory."""
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
        )

        # Add any custom filters or globals here if needed, e.g.:
        # self.env.filters['upper'] = str.upper

    def render(self, template_name: str, data: dict) -> str:
        """Render a template with provided data."""
        template: Template = self.env.get_template(template_name)
        return template.render(**data)
