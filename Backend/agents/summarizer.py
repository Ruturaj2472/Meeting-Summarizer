from crewai import Agent, Task
from agents.base import AgentRun, kickoff, model_for
from models.schemas import SummaryOutput

FALLBACK = {
    "overview": "Summary unavailable",
    "key_points": [],
    "decisions": ""
}

async def run_summarizer(transcript: str, model: str = None) -> AgentRun:
    model = model or model_for("summarizer")

    summarizer_agent = Agent(
        role="Meeting Secretary",
        goal="Write a concise, accurate summary of a meeting transcript",
        backstory="""You are an expert meeting secretary who has summarised
        thousands of meetings. You write clear, neutral summaries that capture
        the key discussion points, decisions made, and overall outcome.
        You never include action items in the summary — those are tracked separately.""",
        verbose=False,
        allow_delegation=False,
        llm=model
    )

    summary_task = Task(
        description=f"""Read the following meeting transcript and write a summary.

        The summary must include:
        1. What the meeting was about (1 sentence)
        2. Key discussion points (2-3 bullet points)
        3. Decisions made during the meeting (1-2 sentences)

        Do NOT include action items — those are handled separately.
        Keep the total summary under 100 words.
        Use plain text only — no markdown, no asterisks, no bold.

        Transcript:
        {transcript}""",
        expected_output="An overview, 2-3 key points and the decisions made",
        output_pydantic=SummaryOutput,
        agent=summarizer_agent
    )

    return await kickoff(summarizer_agent, summary_task, model, FALLBACK)
