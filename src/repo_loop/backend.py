"""Explicit handoff boundary for loop-runtime backends."""

from __future__ import annotations

import shlex
import subprocess
from collections.abc import Mapping, Sequence

BACKEND_ENVIRONMENT_KEY = "REPO_LOOP_BACKEND"


class BackendUnavailable(RuntimeError):
    """Raised when a runtime command has no configured backend."""


def forward_to_backend(arguments: Sequence[str], environ: Mapping[str, str]) -> int:
    """Forward validated arguments to a configured backend without a shell."""
    configured = environ.get(BACKEND_ENVIRONMENT_KEY, "").strip()
    if not configured:
        raise BackendUnavailable(
            "runtime backend is not configured; set REPO_LOOP_BACKEND to an "
            "executable command"
        )

    command = shlex.split(configured)
    if not command:
        raise BackendUnavailable(
            "runtime backend is not configured; REPO_LOOP_BACKEND is empty"
        )

    result = subprocess.run([*command, *arguments], check=False)
    return result.returncode
