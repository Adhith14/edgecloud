# ============================================================

# escalation.py — Cloud Escalation (Dynamic Routing, Option A)

# ============================================================

# When a local agent's output scores below the threshold, the

# same task is escalated to the cloud model for a better answer.

# This is the core of the dynamic routing mechanism.

# ============================================================



import openai

from config import CLOUD_ESCALATION_MODEL, CLOUD_TEMPERATURE


def escalate_to_cloud(task_description: str, task_input: str, client: openai.OpenAI) -> dict:

    """

    Sends a task that the local agent handled poorly to the cloud

    model for a stronger answer.



    Args:

        task_description: what the task is asking for

        task_input: the actual data/content for the task (log text, document, etc.)

        client: the initialised OpenAI client



    Returns:

        dict with 'output' (the cloud's answer) and 'tokens_used'

    """



    # Build a prompt combining the task and its input

    prompt = f"""You are an expert assistant handling a task that a smaller

local model was unable to complete satisfactorily.



TASK: {task_description}



INPUT:

{task_input}



Provide a high-quality, complete response to the task."""



    response = client.chat.completions.create(

        model=CLOUD_ESCALATION_MODEL,

        messages=[{"role": "user", "content": prompt}],

        max_tokens=600,

        temperature=CLOUD_TEMPERATURE

    )



    return {

        "output": response.choices[0].message.content.strip(),

        "tokens_used": response.usage.total_tokens

    }