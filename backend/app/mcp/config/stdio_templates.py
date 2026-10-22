"""Define operator-approved templates for local stdio MCP servers.

Users may select a template code and provide only the options that template
allows. Executable paths and fixed arguments come from trusted application
configuration, so persisted user data can never become an arbitrary command.
The production template catalog is intentionally empty until an operator adds
and reviews a real server configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ApprovedStdioServerTemplate:
    """Describe one trusted stdio command and its allowed user option names."""

    # Stable code saved in the database and displayed as a selectable template.
    code: str
    # Friendly label for a future settings screen.
    name: str
    # Trusted absolute executable path; users never provide or replace it.
    command: str
    # Trusted fixed arguments supplied by the application operator.
    fixed_args: tuple[str, ...] = ()
    # Trusted environment values supplied by the operator, never by the UI.
    fixed_environment: Mapping[str, str] = field(
        default_factory=dict,
        repr=False,
    )
    # User configuration is rejected unless every key appears in this set.
    allowed_configuration_keys: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        """Reject incomplete templates and commands that rely on shell lookup."""
        if not self.code.strip():
            raise ValueError("Stdio template code cannot be empty.")
        if not self.name.strip():
            raise ValueError("Stdio template name cannot be empty.")
        if not self.command.strip() or not Path(self.command).is_absolute():
            raise ValueError(
                "Approved stdio template commands must use an absolute path."
            )
        if any(
            not isinstance(key, str)
            or not key
            or not isinstance(value, str)
            for key, value in self.fixed_environment.items()
        ):
            raise ValueError(
                "Approved stdio template environment values must be strings."
            )


# Phase 2 defines the safe boundary but does not approve or launch a production
# server. Deployments can build a reviewed mapping without changing persistence.
DEFAULT_STDIO_SERVER_TEMPLATES: Mapping[
    str,
    ApprovedStdioServerTemplate,
] = MappingProxyType({})
