from crewai import Agent, Task, Crew
from dotenv import load_dotenv
import re
import json

load_dotenv()

def run_reminder_drafter(assignee: str, action_items: list, meeting_title: str) -> dict:
    items_text = "\n".join([
        f"- {item['text']}"
        for item in action_items
    ])

    reminder_agent = Agent(
        role="Executive Assistant",
        goal="Write short, friendly but professional reminder emails for individual team members",
        backstory="""You are a highly organised executive assistant who sends 
        personalised reminders to team members. Your reminders are warm, 
        direct, and never make people feel micromanaged. You always mention 
        the specific tasks the person is responsible for.""",
        verbose=False,
        allow_delegation=False,
        llm="gpt-4o-mini"
    )

    reminder_task = Task(
        description=f"""Write a short reminder email to {assignee} about their action items 
        from the meeting: "{meeting_title}".

        Their specific tasks are:
        {items_text}

        Requirements:
        - Address the email directly to {assignee} by first name
        - Mention the meeting name
        - List only their specific tasks clearly
        - Keep it friendly, not pushy
        - Under 100 words total
        - Plain text only, no markdown, no asterisks

        You MUST respond with ONLY a valid JSON object in exactly this format:
        {{
            "subject": "your subject line here",
            "body": "your full email body here"
        }}

        Do not include any explanation or text outside the JSON.""",
        expected_output="A valid JSON object with subject and body fields",
        agent=reminder_agent
    )

    crew = Crew(
        agents=[reminder_agent],
        tasks=[reminder_task],
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
        "subject": f"Quick reminder — your action items from {meeting_title}",
        "body": f"Hi {assignee},\n\nJust a quick reminder of your action items:\n\n{items_text}\n\nThanks!"
    }