import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "Backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite://")


@pytest.fixture
def fake_crew(monkeypatch):
    """Replace CrewAI in an agent module so kickoff() returns canned LLM output."""
    def _install(module, output):
        task_cls = MagicMock()
        crew_cls = MagicMock()
        crew_cls.return_value.kickoff.return_value = output
        monkeypatch.setattr(module, "Agent", MagicMock())
        monkeypatch.setattr(module, "Task", task_cls)
        monkeypatch.setattr(module, "Crew", crew_cls)
        return task_cls, crew_cls
    return _install
