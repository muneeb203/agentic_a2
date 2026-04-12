import json
import os
import requests
from dotenv import load_dotenv

from agents.ceo_agent import run_ceo, review_product_spec
from agents.product_agent import run_product
from agents.engineer_agent import run_engineer
from agents.marketing_agent import run_marketing
from agents.qa_agent import run_qa
from message_bus import send_message, get_messages, get_full_log, save_message_history

load_dotenv()

# ============================================================
# YOUR STARTUP IDEA — Change this to your idea!
# ============================================================
STARTUP_IDEA = (
    "A mobile app for residential flat societies where residents can report maintenance "
    "problems to the admin, track complaint status in real-time, and access an AI-powered "
    "residential guide to get instant answers about society rules, amenities, and procedures."
)
# ============================================================


def main():
    print("=" * 60)
    print(" LAUNCHMIND MULTI-AGENT SYSTEM STARTING")
    print("=" * 60)
    print(f"\n Startup Idea: {STARTUP_IDEA}\n")

    # ── STEP 1: CEO decomposes idea and tasks Product agent ──
    run_ceo(STARTUP_IDEA)

    # ── STEP 2: Product Agent generates spec ──
    spec = run_product()

    # ── STEP 3: CEO REVIEWS the spec (FEEDBACK LOOP — worth 25%!) ──
    print("\n CEO reviewing Product spec...")
    ceo_msgs = get_messages("ceo")
    spec_data = None

    for m in ceo_msgs:
        if m["from_agent"] == "product" and "spec" in m["payload"]:
            spec_data = m["payload"]["spec"]

    if spec_data:
        verdict = review_product_spec(spec_data)
        print(f"\n  CEO verdict: {verdict['verdict'].upper()}")
        print(f"  Feedback: {verdict['feedback']}")

        if verdict["verdict"] == "fail":
            print("\n CEO requesting revision from Product Agent!")
            send_message("ceo", "product", "revision_request", {
                "feedback": verdict["feedback"],
                "original_idea": STARTUP_IDEA
            })
            # Product agent revises the spec
            spec_data = run_product()
            print("\n Product Agent revised spec based on CEO feedback.")
    else:
        print("  CEO could not find spec to review.")
        spec_data = spec

    # ── STEP 4: Engineer + Marketing run in parallel (simulated) ──
    pr_url, issue_url = run_engineer()
    pr_url = pr_url if pr_url else "https://github.com/muneeb203/agentic_a2"

    copy = run_marketing(pr_url=pr_url)

    # ── STEP 5: QA Agent reviews everything ──
    all_ceo_msgs = get_messages("ceo")
    html_content = ""
    for m in all_ceo_msgs:
        if m["from_agent"] == "engineer" and "html" in m["payload"]:
            html_content = m["payload"]["html"]

    send_message("ceo", "qa", "task", {
        "html": html_content,
        "copy": copy,
        "spec": spec_data,
        "pr_url": pr_url
    })

    qa_result = run_qa()

    # ── STEP 6: CEO handles QA fail — 2nd feedback loop (Bonus!) ──
    if qa_result and qa_result.get("verdict") == "fail":
        print("\n QA FAILED — CEO requesting Engineer revision!")
        send_message("ceo", "engineer", "revision_request", {
            "issues": qa_result.get("html_issues", []),
            "feedback": "Fix all HTML issues found by QA Agent before launch."
        })

    # ── STEP 7: CEO posts final summary to Slack ──
    print("\n CEO posting final summary to Slack...")
    try:
        qa_verdict = qa_result.get("verdict", "N/A").upper() if qa_result else "N/A"

        # Clean PR URL display
        if pr_url and pr_url != "https://github.com/muneeb203/agentic_a2":
            pr_display = f"<{pr_url}|View on GitHub>"
        else:
            pr_display = "<https://github.com/muneeb203/agentic_a2|View Repo> (PR pending — fix GitHub token)"

        summary = {
            "channel": "#agentic",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "✅ LaunchMind Run Complete!"}
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"* Idea:*\n{STARTUP_IDEA}\n\n"
                            f"* PR:* {pr_display}\n"
                            f"* QA Verdict:* {qa_verdict}\n"
                            f"* Agents Run:* CEO → Product → Engineer + Marketing → QA → CEO"
                        )
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"* Tagline:*\n{copy.get('tagline', 'N/A') if copy else 'N/A'}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"* Twitter:*\n{copy.get('twitter_post', 'N/A') if copy else 'N/A'}"
                        }
                    ]
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": " Powered by LaunchMind Multi-Agent System"}
                    ]
                }
            ]
        }

        res = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {os.environ["SLACK_BOT_TOKEN"]}'},
            json=summary
        )
        if res.json().get("ok"):
            print(" Final summary posted to Slack!")
        else:
            print(f" Slack error: {res.json().get('error')}")
    except Exception as e:
        print(f" Could not post to Slack: {e}")

    # ── STEP 8: Print full message log ──
    print("\n" + "=" * 60)
    print(" FULL MESSAGE LOG:")
    for msg in get_full_log():
        print(f"  [{msg['from_agent'].upper()} → {msg['to_agent'].upper()}] "
              f"type={msg['message_type']}  id={msg['message_id'][:8]}...")

    # ── STEP 9: Persist full message history to JSON ──
    save_message_history("message_history.json")

    print("\n LaunchMind complete!")


if __name__ == "__main__":
    main()