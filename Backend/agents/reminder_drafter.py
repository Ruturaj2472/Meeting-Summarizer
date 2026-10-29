from crewai import Agent, Task
from agents.base import AgentRun, kickoff, model_for
from models.schemas import EmailDraft

async def run_reminder_drafter(assignee: str, action_items: list, meeting_title: str, model: str = None) -> AgentRun:
    model = model or model_for("reminder_drafter")

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
        llm=model
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
        - Plain text only, no markdown, no asterisks""",
        expected_output="A subject line and a short plain-text reminder email body",
        output_pydantic=EmailDraft,
        agent=reminder_agent
    )

    fallback = {
        "subject": f"Quick reminder — your action items from {meeting_title}",
        "body": f"Hi {assignee},\n\nJust a quick reminder of your action items:\n\n{items_text}\n\nThanks!"
    }
    return await kickoff(reminder_agent, reminder_task, model, fallback)
