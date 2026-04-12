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


def clean_json(text):
    """Clean and extract JSON from LLM response."""
    text = text.strip()
    # Remove markdown code blocks
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break
    # Find the first { and last } to extract JSON
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text


def run_product():
    print("\n Product Agent waiting for task...")
    messages = get_messages("product")
    if not messages:
        print("No messages for Product Agent.")
        return None

    msg = messages[0]
    idea = msg["payload"].get("idea") or msg["payload"].get("startup_idea") or msg["payload"].get("original_idea", "")
    focus = msg["payload"].get("focus") or msg["payload"].get("revision_notes", "")
    parent_id = msg["message_id"]

    print(f" Product Agent generating spec for: {idea}")

    # Retry up to 3 times if JSON is bad
    for attempt in range(3):
        try:
            result = call_llm(
                system_prompt="You are an expert Product Manager. Return ONLY valid JSON. No extra text, no markdown, no code blocks. Just pure JSON.",
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
                IMPORTANT: Return ONLY the JSON object. Nothing else.
                '''
            )
            cleaned = clean_json(result)
            spec = json.loads(cleaned)
            print(f"\n Product spec created: {spec['value_proposition']}")

            send_message("product", "engineer", "task", {"spec": spec}, parent_id)
            send_message("product", "marketing", "task", {"spec": spec}, parent_id)
            send_message("product", "ceo", "confirmation", {
                "status": "spec_ready",
                "spec": spec
            }, parent_id)

            return spec

        except json.JSONDecodeError as e:
            print(f" JSON parse failed (attempt {attempt+1}/3): {e}")
            if attempt == 2:
                print(" Could not parse JSON after 3 attempts.")
                raise

    return None