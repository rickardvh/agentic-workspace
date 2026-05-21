from __future__ import annotations

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        if self.target_name != "wheel":
            return
        root = Path(self.root)
        embedded_generated_root = root / "src" / "repo_planning_bootstrap" / "_generated_cli_package_impl"
        if not (embedded_generated_root / "cli.py").is_file():
            return

        force_include = self.build_config.force_include
        for source, destination in list(force_include.items()):
            destination_path = Path(destination)
            if destination_path.parts[:3] != ("src", "repo_planning_bootstrap", "_generated_cli_package_impl"):
                continue
            if not Path(source).exists() and (root / destination_path).exists():
                del force_include[source]
