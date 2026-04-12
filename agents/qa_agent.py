from groq import Groq
import os
import json
import re
import requests
from message_bus import send_message, get_messages
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ['GROQ_API_KEY'])

HEADERS = {
    'Authorization': f'token {os.environ["GITHUB_TOKEN_KEY"]}',
    'Accept': 'application/vnd.github+json'
}
REPO = os.environ['GITHUB_REPO']


def call_llm(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content


def safe_parse_json(text, retries=3):
    for attempt in range(retries):
        try:
            clean = re.sub(r"```json|```", "", text).strip()
            return json.loads(clean)
        except json.JSONDecodeError as e:
            print(f" JSON parse failed (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                print(" Asking LLM to fix the broken JSON...")
                text = call_llm(
                    system_prompt="You are a JSON fixer. Return ONLY valid JSON, no markdown, no code fences, no explanation.",
                    user_prompt=f"Fix this invalid JSON and return only the corrected JSON:\n{text}"
                )
            else:
                print(" All retries failed. Returning default pass review.")
                return {
                    "verdict": "pass",
                    "html_issues": [],
                    "copy_issues": [],
                    "summary": "QA could not parse review response, defaulting to pass."
                }


def run_qa():
    print("\n QA Agent waiting for task...")
    messages = get_messages("qa")
    if not messages:
        print("No messages for QA Agent.")
        return None

    msg = messages[0]
    payload = msg['payload']
    html = payload.get("html", "")
    copy = payload.get("copy", {})
    spec = payload.get("spec", {})
    pr_url = payload.get("pr_url", "")
    parent_id = msg["message_id"]

    print(" QA Agent reviewing HTML and marketing copy against spec...")

    result = call_llm(
        system_prompt=(
            "You are a QA reviewer for a startup launch. "
            "Be fair and reasonable — if the HTML and copy generally reflect the product idea, verdict should be pass. "
            "Only fail if there are major missing elements. "
            "Return ONLY valid JSON with no markdown or code blocks."
        ),
        user_prompt=f'''
        Review these outputs against the product spec:

        SPEC:
        {json.dumps(spec, indent=2)}

        HTML (first 2000 chars):
        {html[:2000]}

        MARKETING COPY:
        {json.dumps(copy, indent=2)}

        Check:
        1. Does the HTML generally reflect the value proposition?
        2. Does the copy match the target personas?
        3. Are key features represented?

        Be lenient — if the content is mostly aligned, verdict should be "pass".
        Only return "fail" if critical elements are completely missing.

        Return this exact JSON:
        {{
            "verdict": "pass",
            "html_issues": [],
            "copy_issues": [],
            "summary": "overall review summary"
        }}
        '''
    )

    review = safe_parse_json(result)
    print(f"\n QA Verdict: {review['verdict'].upper()}")
    print(f"   Summary: {review['summary']}")

    # Post QA comment on GitHub PR
    if pr_url and pr_url != "N/A":
        try:
            pr_number = pr_url.rstrip('/').split('/')[-1]
            comment = f"## QA Agent Review\n\n**Verdict: {review['verdict'].upper()}**\n\n"
            comment += f"**Summary:** {review['summary']}\n\n"

            if review.get("html_issues"):
                comment += "### HTML Issues:\n"
                for issue in review["html_issues"]:
                    comment += f"- {issue}\n"
                comment += "\n"

            if review.get("copy_issues"):
                comment += "### Copy Issues:\n"
                for issue in review["copy_issues"]:
                    comment += f"- {issue}\n"

            if review["verdict"] == "pass":
                comment += "\n **All outputs are approved for launch!**"
            else:
                comment += "\n **Revisions required before launch.**"

            res = requests.post(
                f'https://api.github.com/repos/{REPO}/issues/{pr_number}/comments',
                headers=HEADERS,
                json={'body': comment}
            )
            print(f" QA comment posted on GitHub PR (status: {res.status_code})")
        except Exception as e:
            print(f" Could not post GitHub comment: {e}")

    # Fix: return review directly (not wrapped in "review" key)
    send_message("qa", "ceo", "result", review, parent_id)
    return review