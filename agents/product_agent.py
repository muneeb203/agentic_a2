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
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text


def run_product():
    print("\n📦 Product Agent waiting for task...")
    messages = get_messages("product")
    if not messages:
        print("No messages for Product Agent.")
        return None

    msg = messages[0]
    idea = msg["payload"]["idea"]
    focus = msg["payload"].get("focus", "")
    parent_id = msg["message_id"]

    print(f"📦 Product Agent generating spec for: {idea}")

    result = call_llm(
        system_prompt="You are an expert Product Manager. Return ONLY valid JSON.",
        user_prompt=f'''
        Startup: {idea}
        Focus: {focus}

        Return this exact JSON structure:
        {{
            "value_proposition": "one clear sentence",
            "personas": [
                {{"name": "Name", "role": "role", "pain_point": "problem they face"}}
            ],
            "features": [
                {{"name": "Feature Name", "description": "what it does", "priority": 1}}
            ],
            "user_stories": [
                {{"as_a": "user type", "i_want": "action", "so_that": "benefit"}}
            ]
        }}
        Include 2 personas, 5 features, 3 user stories.
        '''
    )

    spec = json.loads(result)
    print(f"\n✅ Product spec created: {spec['value_proposition']}")

    # Send spec to both Engineer and Marketing agents
    send_message("product", "engineer", "task", {"spec": spec}, parent_id)
    send_message("product", "marketing", "task", {"spec": spec}, parent_id)
    send_message("product", "ceo", "confirmation", {
        "status": "spec_ready",
        "spec": spec
    }, parent_id)

    return spec
