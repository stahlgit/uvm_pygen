"""
Project Name: uvm_pygen
File Name: renderer.py
Description: Module for rendering templates using Jinja2.
Author: Peter Stahl (xstahl01@stud.fit.vut.cz)
Date: 2026-05-11
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from jinja2.environment import Template


class TemplateRenderer:
    """Handles Jinja2 environment and template rendering."""

    # Absolute path to the bundled templates directory — resolved once at import
    # time so the renderer works regardless of the working directory.
    # renderer.py lives at uvm_pygen/services/generation/ → .parent×3 = uvm_pygen/
    _DEFAULT_TEMPLATE_DIR: Path = Path(__file__).parent.parent.parent / "templates"

    def __init__(self, template_dir: str | Path | None = None) -> None:
        """Initialize the Jinja2 environment with the specified template directory."""
        if template_dir is None:
            template_dir = self._DEFAULT_TEMPLATE_DIR
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            extensions=["jinja2.ext.loopcontrols"],
        )

        # Add any custom filters or globals here if needed, e.g.:
        # self.env.filters['upper'] = str.upper

    def render(self, template_name: str, data: dict) -> str:
        """Render a template with provided data."""
        template: Template = self.env.get_template(template_name)
        return template.render(**data)
