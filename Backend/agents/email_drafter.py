from crewai import Agent, Task
from agents.base import AgentRun, kickoff, model_for
from models.schemas import EmailDraft

async def run_email_drafter(action_items: list, summary: dict = None, model: str = None) -> AgentRun:
    model = model or model_for("email_drafter")

    if not action_items:
        return AgentRun(
            data={
                "subject": "Meeting Summary",
                "body": "Please find the meeting summary below. No action items were identified."
            },
            model=model
        )

    pending_items = [i for i in action_items if i.get("status", "pending") == "pending"]
    done_items = [i for i in action_items if i.get("status", "pending") == "done"]

    pending_text = "\n".join([
        f"- {item.get('text', '')} (Assignee: {item.get('assignee') or 'Unassigned'})"
        for item in pending_items
    ]) if pending_items else "None"

    done_text = "\n".join([
        f"- {item.get('text', '')}"
        for item in done_items
    ]) if done_items else ""

    summary_text = ""
    if summary and summary.get("overview"):
        summary_text = f"Meeting overview: {summary.get('overview', '')}"

    drafter_agent = Agent(
        role="Executive Assistant",
        goal="Write clear, professional follow-up emails summarizing meeting outcomes and outstanding tasks",
        backstory="""You are a highly skilled executive assistant known for writing
        concise, professional emails that busy professionals actually read.
        Your emails are friendly but direct, well structured, and always under 250 words.
        You never use markdown formatting like asterisks or bold — plain text only.""",
        verbose=False,
        allow_delegation=False,
        llm=model
    )

    drafting_task = Task(
        description=f"""Write a professional follow-up email for a meeting.

    {f'Meeting context: {summary_text}' if summary_text else ''}

    Pending action items (include ALL of these, every single one):
    {pending_text}

    {f'Completed items:{chr(10)}{done_text}' if done_text else ''}

    You MUST follow this exact structure and format for the body:

    Hi team,

    [One sentence meeting recap if context provided, otherwise skip this line]

    Here are the outstanding action items:

    [List every pending item on its own line like this:]
    - Task description (Owner: Assignee name)
    - Task description (Owner: Assignee name)

    [If there are completed items, add:]
    Completed:
    - Task description

    Please ensure your tasks are completed on time. Reply if you have any questions.

    Best regards,
    [Your Name]

    Rules:
    - Use ONLY plain text, NO markdown, NO asterisks, NO bold, NO bullet symbols other than dashes
    - Every pending item must appear on its own line starting with a dash
    - Do not group items under sub-headers
    - Do not skip any pending items
    - Keep it under 250 words""",
        expected_output="A subject line and a plain-text email body",
        output_pydantic=EmailDraft,
        agent=drafter_agent
    )

    fallback = {
        "subject": "Meeting Follow-up: Action Items",
        "body": f"Hi team,\n\nPlease find below the outstanding action items from our meeting:\n\n{pending_text}\n\nThanks"
    }
    return await kickoff(drafter_agent, drafting_task, model, fallback)
