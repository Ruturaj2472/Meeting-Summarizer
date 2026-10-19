from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

def run_extractor(transcript: str) -> dict:
    extractor_agent = Agent(
        role="Meeting Analyst",
        goal="Extract all action items and generate a concise meeting title from a transcript",
        backstory="""You are an expert meeting analyst who has processed thousands 
        of meeting transcripts. You are precise, thorough, and always identify 
        every commitment and task mentioned in a conversation.""",
        verbose=False,
        allow_delegation=False,
        llm="gpt-4o"
    )

    extraction_task = Task(
        description=f"""Analyze the following meeting transcript and extract:
        1. A short 5-7 word title summarizing the meeting topic
        2. All action items mentioned — things people agreed to do

        For each action item extract:
        - text: what needs to be done
        - assignee: who is responsible (null if not mentioned)

        Transcript:
        {transcript}

        You MUST respond with ONLY a valid JSON object in exactly this format:
        {{
            "title": "short meeting title here",
            "action_items": [
                {{"text": "action item description", "assignee": "person name or null"}},
                {{"text": "another action item", "assignee": "person name or null"}}
            ]
        }}

        Do not include any explanation or text outside the JSON.""",
        expected_output="A valid JSON object with title and action_items fields",
        agent=extractor_agent
    )

    crew = Crew(
        agents=[extractor_agent],
        tasks=[extraction_task],
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
        "title": "Untitled Meeting",
        "action_items": []
    }