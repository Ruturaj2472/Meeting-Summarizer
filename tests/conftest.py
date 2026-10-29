import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Backend"))
sys.path.insert(0, str(ROOT / "evals"))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


@pytest.fixture
def fake_crew(monkeypatch):
    """Replace CrewAI's Crew so kickoff_async() returns a canned result instead of calling OpenAI.

    `parsed` is what CrewAI would put in result.pydantic (None means validation failed).
    """
    from agents import base

    def _install(parsed=None, prompt_tokens=0, completion_tokens=0):
        result = SimpleNamespace(
            pydantic=parsed,
            token_usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
        )
        crew_cls = MagicMock()
        crew_cls.return_value.kickoff_async = AsyncMock(return_value=result)
        monkeypatch.setattr(base, "Crew", crew_cls)
        return crew_cls
    return _install


def crew_task(crew_cls):
    """The Task object the agent handed to Crew(...)."""
    return crew_cls.call_args.kwargs["tasks"][0]
