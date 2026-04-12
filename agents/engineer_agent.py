from groq import Groq
import os
import json
import requests
import base64
from message_bus import send_message, get_messages
from dotenv import load_dotenv
import time

load_dotenv()

client = Groq(api_key=os.environ['GROQ_API_KEY'])

GITHUB_TOKEN_KEY = os.environ['GITHUB_TOKEN_KEY']
REPO = os.environ['GITHUB_REPO']
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN_KEY}",
    "Accept": "application/vnd.github+json"
}


def call_llm(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content


def get_main_sha():
    r = requests.get(
        f'https://api.github.com/repos/{REPO}/git/ref/heads/main',
        headers=HEADERS
    )
    return r.json()["object"]["sha"]


def delete_branch_if_exists(branch):
    """Delete branch if it already exists to avoid 422 on creation."""
    r = requests.delete(
        f'https://api.github.com/repos/{REPO}/git/refs/heads/{branch}',
        headers=HEADERS
    )
    if r.status_code == 204:
        print(f"  Old branch '{branch}' deleted successfully.")
    elif r.status_code == 422:
        print(f"  Branch '{branch}' did not exist, skipping delete.")


def get_file_sha(branch, filename="index.html"):
    """Get existing file SHA if it exists on the branch (needed for updates)."""
    r = requests.get(
        f'https://api.github.com/repos/{REPO}/contents/{filename}',
        headers=HEADERS,
        params={"ref": branch}
    )
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def run_engineer():
    print("\n Engineer Agent waiting for task...")
    messages = get_messages("engineer")
    if not messages:
        print("No messages for Engineer Agent.")
        return None, None

    msg = messages[0]
    spec = msg["payload"]["spec"]
    parent_id = msg["message_id"]

    print(" Engineer Agent generating HTML landing page...")

    html = call_llm(
        system_prompt="You are a frontend developer. Return ONLY raw HTML code, no markdown, no explanation, no code blocks.",
        user_prompt=f'''
        Create a beautiful, modern HTML landing page for this startup:
        Value Proposition: {spec["value_proposition"]}
        Features: {json.dumps(spec["features"])}
        Personas: {json.dumps(spec["personas"])}

        Include:
        - A compelling hero section with headline and subheadline
        - A features section showcasing all features
        - A call-to-action button
        - Inline CSS for a clean, professional design
        - Responsive layout
        Make it visually impressive with a dark gradient header.
        '''
    )

    if html.strip().startswith("```"):
        html = html.strip().split("```")[1]
        if html.startswith("html"):
            html = html[4:]
    html = html.strip()

    print(" Engineer creating GitHub branch, committing file, opening PR...")

    # Use unique branch name per run to avoid 422
    branch = f"agent-landing-page-{int(time.time())}"
    sha = get_main_sha()

    # Create fresh branch
    branch_res = requests.post(
        f'https://api.github.com/repos/{REPO}/git/refs',
        headers=HEADERS,
        json={"ref": f"refs/heads/{branch}", "sha": sha}
    )
    print(f"  Branch creation: {branch_res.status_code}")

    if branch_res.status_code not in [200, 201]:
        print(f"  Branch error: {branch_res.json()}")

    # Get file SHA if file already exists on branch
    file_sha = get_file_sha(branch)

    content_b64 = base64.b64encode(html.encode()).decode()
    commit_payload = {
        "message": "feat: Add AI-generated landing page",
        "content": content_b64,
        "branch": branch,
        "author": {"name": "EngineerAgent", "email": "agent@launchmind.ai"}
    }

    # If file already exists, include its SHA to update instead of create
    if file_sha:
        commit_payload["sha"] = file_sha

    commit_res = requests.put(
        f'https://api.github.com/repos/{REPO}/contents/index.html',
        headers=HEADERS,
        json=commit_payload
    )
    print(f"  Commit: {commit_res.status_code}")

    if commit_res.status_code not in [200, 201]:
        print(f"  Commit error: {commit_res.json()}")

    # Create GitHub Issue
    issue_res = requests.post(
        f'https://api.github.com/repos/{REPO}/issues',
        headers=HEADERS,
        json={
            "title": "Initial landing page creation",
            "body": f"Create landing page for: {spec['value_proposition']}\n\nFeatures to highlight:\n" +
                    "\n".join([f"- {f['name']}: {f['description']}" for f in spec['features']])
        }
    )
    issue_url = issue_res.json().get("html_url", "N/A")
    print(f"  Issue created: {issue_url}")

    # Create Pull Request
    pr_res = requests.post(
        f'https://api.github.com/repos/{REPO}/pulls',
        headers=HEADERS,
        json={
            "title": "feat: AI-generated landing page",
            "body": f"Landing page for: {spec['value_proposition']}\n\nGenerated by EngineerAgent 🤖",
            "head": branch,
            "base": "main"
        }
    )
    pr_data = pr_res.json()
    pr_url = pr_data.get("html_url", "N/A")

    if pr_url == "N/A":
        print(f"  PR error: {pr_data.get('message', 'Unknown error')}")
    
    print(f" Engineer done! PR: {pr_url}")

    send_message("engineer", "ceo", "result", {
        "pr_url": pr_url,
        "issue_url": issue_url,
        "html": html
    }, parent_id)

    return pr_url, issue_url