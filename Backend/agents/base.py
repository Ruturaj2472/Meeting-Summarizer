from crewai import Crew
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import time

load_dotenv()

DEFAULT_MODELS = {
    "extractor": "gpt-4o",
    "summarizer": "gpt-4o-mini",
    "email_drafter": "gpt-4o-mini",
    "reminder_drafter": "gpt-4o-mini",
}

# USD per 1M tokens (input, output) — update if OpenAI pricing changes
PRICES = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}

def model_for(agent_name: str) -> str:
    """Model for an agent, overridable with e.g. EXTRACTOR_MODEL=gpt-4o-mini."""
    return os.getenv(f"{agent_name.upper()}_MODEL", DEFAULT_MODELS[agent_name])

@dataclass
class AgentRun:
    data: dict
    model: str
    seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    fallback: bool = False

    @property
    def cost_usd(self) -> float:
        input_price, output_price = PRICES.get(self.model, (0.0, 0.0))
        return (self.prompt_tokens * input_price + self.completion_tokens * output_price) / 1_000_000

    def metrics(self) -> dict:
        return {
            "model": self.model,
            "seconds": round(self.seconds, 2),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "fallback": self.fallback,
        }

async def kickoff(agent, task, model: str, fallback: dict) -> AgentRun:
    """Run a single-task crew without blocking the event loop.

    The task's output_pydantic schema is enforced by CrewAI; if the reply still
    can't be validated, the safe fallback is returned instead of raising.
    """
    crew = Crew(agents=[agent], tasks=[task], verbose=False)

    start = time.perf_counter()
    result = await crew.kickoff_async()
    seconds = time.perf_counter() - start

    usage = getattr(result, "token_usage", None)
    run = AgentRun(
        data=dict(fallback),
        model=model,
        seconds=seconds,
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        fallback=True,
    )

    parsed = getattr(result, "pydantic", None)
    if parsed is not None:
        run.data = parsed.model_dump()
        run.fallback = False
    return run
