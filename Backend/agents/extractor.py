from crewai import Agent, Task
from agents.base import AgentRun, kickoff, model_for
from models.schemas import ExtractionOutput

FALLBACK = {
    "title": "Untitled Meeting",
    "action_items": []
}

async def run_extractor(transcript: str, model: str = None) -> AgentRun:
    model = model or model_for("extractor")

    extractor_agent = Agent(
        role="Meeting Analyst",
        goal="Extract all action items and generate a concise meeting title from a transcript",
        backstory="""You are an expert meeting analyst who has processed thousands
        of meeting transcripts. You are precise, thorough, and always identify
        every commitment and task mentioned in a conversation.""",
        verbose=False,
        allow_delegation=False,
        llm=model
    )

    extraction_task = Task(
        description=f"""Analyze the following meeting transcript and extract:
        1. A short 5-7 word title summarizing the meeting topic
        2. All action items mentioned — things people agreed to do

        For each action item extract:
        - text: what needs to be done
        - assignee: who is responsible (null if not mentioned)

        Only include real commitments. Ideas that were rejected or postponed
        without an owner are not action items.

        Transcript:
        {transcript}""",
        expected_output="The meeting title and every action item with its assignee",
        output_pydantic=ExtractionOutput,
        agent=extractor_agent
    )

    return await kickoff(extractor_agent, extraction_task, model, FALLBACK)
