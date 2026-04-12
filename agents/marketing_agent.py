from groq import Groq
import os
import json
import re
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
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
                print(" All retries failed. Could not parse JSON.")
                raise


def run_marketing(pr_url=None):
    print("\n Marketing Agent waiting for task...")
    messages = get_messages("marketing")
    if not messages:
        print("No messages for Marketing Agent.")
        return None

    msg = messages[0]
    spec = msg["payload"]["spec"]
    parent_id = msg["message_id"]

    print(" Marketing Agent generating copy...")

    result = call_llm(
        system_prompt=(
            "You are a growth marketer. Return ONLY a valid JSON object. "
            "No markdown, no code fences, no explanation. "
            "Ensure all strings use escaped quotes and all fields are comma-separated."
        ),
        user_prompt=f'''
        Generate marketing copy for this startup:
        {json.dumps(spec)}

        Return this exact JSON:
        {{
            "tagline": "under 10 words, catchy",
            "short_description": "2-3 sentences explaining the product",
            "email_subject": "compelling cold outreach subject line",
            "email_body": "cold outreach email body, 3-4 paragraphs",
            "twitter_post": "tweet under 280 characters",
            "linkedin_post": "professional linkedin post",
            "instagram_post": "instagram caption with hashtags"
        }}
        '''
    )

    copy = safe_parse_json(result)
    print(f" Copy generated: {copy['tagline']}")

    print(" Sending email via SendGrid...")
    try:
        email_body = f"""
        <h2>{copy['tagline']}</h2>
        <p>{copy['email_body']}</p>
        <br>
        <p><em>Sent by LaunchMind Marketing Agent 🤖</em></p>
        """
        mail_msg = Mail(
            from_email=os.environ['SENDGRID_FROM_EMAIL'],
            to_emails=os.environ['TEST_EMAIL'],
            subject=copy["email_subject"],
            html_content=email_body
        )
        SendGridAPIClient(os.environ['SENDGRID_API_KEY']).send(mail_msg)
        print(" Email sent successfully!")
    except Exception as e:
        print(f" Email failed: {e}")

    print(" Posting to Slack #launches channel...")
    try:
        pr_display = pr_url if pr_url else "N/A"
        payload = {
            "channel": "#agentic",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🚀 {copy['tagline']}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": copy["short_description"]}
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Twitter:*\n{copy['twitter_post']}"},
                        {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_display}|View PR>"}
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*LinkedIn:*\n{copy['linkedin_post']}"}
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "📣 Posted by LaunchMind Marketing Agent 🤖"}
                    ]
                }
            ]
        }
        slack_res = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {os.environ["SLACK_BOT_TOKEN"]}'},
            json=payload
        )
        slack_data = slack_res.json()
        if slack_data.get("ok"):
            print(" Slack message posted!")
        else:
            print(f" Slack error: {slack_data.get('error')}")
    except Exception as e:
        print(f" Slack failed: {e}")

    send_message("marketing", "ceo", "result", {"copy": copy}, parent_id)
    return copy