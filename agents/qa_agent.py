import anthropic
import os
import json
import requests
from message_bus import send_message, get_messages
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
HEADERS = {
    'Authorization': f'token {os.environ["GITHUB_TOKEN"]}',
    'Accept': 'application/vnd.github+json'
}
REPO = os.environ['GITHUB_REPO']


def call_llm(system_prompt, user_prompt):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text


def run_qa():
    print("\n🔍 QA Agent waiting for task...")
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

    print("🔍 QA Agent reviewing HTML and marketing copy against spec...")

    result = call_llm(
        system_prompt="You are a QA reviewer for a startup launch. Be thorough. Return ONLY valid JSON.",
        user_prompt=f'''
        Review these outputs against the product spec:

        SPEC:
        {json.dumps(spec, indent=2)}

        HTML snippet (first 600 chars):
        {html[:600]}

        MARKETING COPY:
        {json.dumps(copy, indent=2)}

        Check:
        1. Does the HTML reflect the value proposition?
        2. Does the copy match the target personas?
        3. Are all key features represented?

        Return:
        {{
            "verdict": "pass" or "fail",
            "html_issues": ["issue1", "issue2"],
            "copy_issues": ["issue1", "issue2"],
            "summary": "overall review summary"
        }}
        '''
    )

    review = json.loads(result)
    print(f"\n🔍 QA Verdict: {review['verdict'].upper()}")
    print(f"   Summary: {review['summary']}")

    # Post review comment on GitHub PR
    if pr_url and pr_url != "N/A":
        try:
            pr_number = pr_url.rstrip('/').split('/')[-1]
            comment = f"## 🤖 QA Agent Review\n\n**Verdict: {review['verdict'].upper()}**\n\n"
            comment += f"**Summary:** {review['summary']}\n\n"

            if review.get("html_issues"):
                comment += "### 🔴 HTML Issues:\n"
                for issue in review["html_issues"]:
                    comment += f"- {issue}\n"
                comment += "\n"

            if review.get("copy_issues"):
                comment += "### 🔴 Copy Issues:\n"
                for issue in review["copy_issues"]:
                    comment += f"- {issue}\n"

            if review["verdict"] == "pass":
                comment += "\n✅ **All outputs are approved for launch!**"

            res = requests.post(
                f'https://api.github.com/repos/{REPO}/issues/{pr_number}/comments',
                headers=HEADERS,
                json={'body': comment}
            )
            print(f"✅ QA comment posted on GitHub PR (status: {res.status_code})")
        except Exception as e:
            print(f"⚠️ Could not post GitHub comment: {e}")

    send_message("qa", "ceo", "result", {"review": review}, parent_id)
    return review
