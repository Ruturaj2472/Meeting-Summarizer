from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import json
import re

load_dotenv()

def run_summarizer(transcript: str) -> dict:
    summarizer_agent = Agent(
        role="Meeting Secretary",
        goal="Write a concise, accurate summary of a meeting transcript",
        backstory="""You are an expert meeting secretary who has summarised 
        thousands of meetings. You write clear, neutral summaries that capture 
        the key discussion points, decisions made, and overall outcome. 
        You never include action items in the summary — those are tracked separately.""",
        verbose=False,
        allow_delegation=False,
        llm="gpt-4o-mini"
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
        {transcript}

        You MUST respond with ONLY a valid JSON object in exactly this format:
        {{
            "overview": "one sentence describing what the meeting was about",
            "key_points": ["point one", "point two", "point three"],
            "decisions": "one or two sentences about decisions made"
        }}

        Do not include any explanation or text outside the JSON.""",
        expected_output="A valid JSON object with overview, key_points, and decisions fields",
        agent=summarizer_agent
    )

    crew = Crew(
        agents=[summarizer_agent],
        tasks=[summary_task],
        verbose=False
    )

    result = crew.kickoff()
    raw = str(result)

    try:
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    return {
        "overview": "Summary unavailable",
        "key_points": [],
        "decisions": ""
    }