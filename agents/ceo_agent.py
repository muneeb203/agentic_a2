from groq import Groq
import os
import json
from message_bus import send_message, get_messages
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ['GROQ_API_KEY'])


def call_llm(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content


def decompose_idea(startup_idea):
    result = call_llm(
        system_prompt="You are a startup CEO. Break a startup idea into tasks. Return ONLY valid JSON with no markdown or code blocks.",
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
    clean = result.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())


def review_product_spec(spec):
    result = call_llm(
        system_prompt="You are a strict startup CEO. Be critical. Return ONLY valid JSON with no markdown or code blocks.",
        user_prompt=f'''
        Review this product spec:
        {json.dumps(spec, indent=2)}
        Return JSON:
        {{
            "verdict": "pass" or "fail",
            "feedback": "detailed feedback here"
        }}
        '''
    )
    clean = result.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())


def run_ceo(startup_idea):
    print(f"\n CEO Agent starting with idea: {startup_idea}")
    tasks = decompose_idea(startup_idea)
    print("\n CEO decomposed idea into tasks:")
    print(json.dumps(tasks, indent=2))
    send_message("ceo", "product", "task", {
        "idea": startup_idea,
        "focus": tasks["product_task"]
    })
    return tasks
