import anthropic
import os
import json
from message_bus import send_message, get_messages
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])


def call_llm(system_prompt, user_prompt):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text


def decompose_idea(startup_idea):
    """LLM Call #1: Break idea into tasks for each agent."""
    result = call_llm(
        system_prompt="You are a startup CEO. Break a startup idea into tasks. Return ONLY valid JSON.",
        user_prompt=f'''
        Startup idea: {startup_idea}

        Create tasks for: product, engineer, marketing agents.
        Return:
        {{
            "product_task": "...",
            "engineer_task": "...",
            "marketing_task": "..."
        }}
        '''
    )
    return json.loads(result)


def review_product_spec(spec):
    """LLM Call #2: Review quality of product spec."""
    result = call_llm(
        system_prompt="You are a strict startup CEO. Be critical. Return ONLY valid JSON.",
        user_prompt=f'''
        Review this product spec:
        {json.dumps(spec, indent=2)}

        Is it specific enough? Does it clearly describe the startup idea?
        Return JSON:
        {{
            "verdict": "pass" or "fail",
            "feedback": "detailed feedback here"
        }}
        '''
    )
    return json.loads(result)


def run_ceo(startup_idea):
    print(f"\n🚀 CEO Agent starting with idea: {startup_idea}")
    tasks = decompose_idea(startup_idea)
    print("\n✅ CEO decomposed idea into tasks:")
    print(json.dumps(tasks, indent=2))

    send_message("ceo", "product", "task", {
        "idea": startup_idea,
        "focus": tasks["product_task"]
    })

    return tasks
