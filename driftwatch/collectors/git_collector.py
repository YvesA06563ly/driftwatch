"""Collector that captures the current state of a Git repository."""
from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, List, Optional

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class GitCollector(BaseCollector):
    """Collect metadata from one or more local Git repositories.

    Config keys:
        repos (list[str]): Absolute paths to git repos. Required.
        include_remotes (bool): Include remote URLs. Default True.
        include_submodules (bool): Include submodule SHAs. Default False.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._repos: List[str] = config.get("repos", [])
        self._include_remotes: bool = config.get("include_remotes", True)
        self._include_submodules: bool = config.get("include_submodules", False)

    def validate_config(self) -> None:
        repos = self._config.get("repos")
        if not repos or not isinstance(repos, list):
            raise ValueError("git_collector requires 'repos' as a non-empty list")
        for r in repos:
            if not isinstance(r, str) or not r.strip():
                raise ValueError(f"git_collector: invalid repo path: {r!r}")

    def _run(self, args: List[str], cwd: str) -> Optional[str]:
        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def collect(self) -> ConfigSnapshot:
        data: Dict[str, Any] = {}
        for repo in self._repos:
            entry: Dict[str, Any] = {}
            entry["commit"] = self._run(["git", "rev-parse", "HEAD"], repo)
            entry["branch"] = self._run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], repo
            )
            raw_status = self._run(["git", "status", "--porcelain"], repo)
            entry["dirty"] = bool(raw_status) if raw_status is not None else None
            if self._include_remotes:
                raw_remotes = self._run(["git", "remote", "-v"], repo)
                remotes: Dict[str, str] = {}
                if raw_remotes:
                    for line in raw_remotes.splitlines():
                        m = re.match(r"^(\S+)\s+(\S+)\s+\(fetch\)$", line)
                        if m:
                            remotes[m.group(1)] = m.group(2)
                entry["remotes"] = remotes
            if self._include_submodules:
                raw_sub = self._run(
                    ["git", "submodule", "status", "--recursive"], repo
                )
                subs: Dict[str, str] = {}
                if raw_sub:
                    for line in raw_sub.splitlines():
                        parts = line.split()
                        if len(parts) >= 2:
                            subs[parts[1]] = parts[0].lstrip("+-U")
                entry["submodules"] = subs
            data[repo] = entry
        return ConfigSnapshot(source="git", data=data)
