import anthropic
import os
import json
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
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


def run_marketing(pr_url=None):
    print("\n📣 Marketing Agent waiting for task...")
    messages = get_messages("marketing")
    if not messages:
        print("No messages for Marketing Agent.")
        return None

    msg = messages[0]
    spec = msg["payload"]["spec"]
    parent_id = msg["message_id"]

    print("📣 Marketing Agent generating copy...")

    # Generate marketing copy with LLM
    result = call_llm(
        system_prompt="You are a growth marketer. Return ONLY valid JSON.",
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

    copy = json.loads(result)
    print(f"✅ Copy generated: {copy['tagline']}")

    # Send Email via SendGrid
    print("📧 Sending email via SendGrid...")
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
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"⚠️ Email failed: {e}")

    # Post to Slack with Block Kit
    print("💬 Posting to Slack #launches channel...")
    try:
        pr_display = pr_url if pr_url else "N/A"
        payload = {
            "channel": "#launches",
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
            print("✅ Slack message posted!")
        else:
            print(f"⚠️ Slack error: {slack_data.get('error')}")
    except Exception as e:
        print(f"⚠️ Slack failed: {e}")

    send_message("marketing", "ceo", "result", {"copy": copy}, parent_id)
    return copy
