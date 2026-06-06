#!/usr/bin/env python3
"""Compatibility entrypoint for the fan-in demux helper."""
import importlib.util
from pathlib import Path


def _load_collect():
    path = Path(__file__).resolve().parents[1] / "collect.py"
    spec = importlib.util.spec_from_file_location("swarm_discussion_collect", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    _load_collect().main()
