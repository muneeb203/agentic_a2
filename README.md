# LaunchMind — Multi-Agent AI Startup Launcher

LaunchMind is an autonomous multi-agent system that takes a startup idea and automatically generates a product spec, builds a landing page, creates marketing copy, sends emails, posts to Slack, and reviews everything using AI agents.

---

## How It Works

LaunchMind uses 5 AI agents that work together in a pipeline:

```
Your Startup Idea
       ↓
   CEO Agent        → Breaks idea into tasks
       ↓
 Product Agent      → Creates product spec, personas, features
       ↓
Engineer Agent      → Builds HTML landing page + GitHub PR
Marketing Agent     → Writes copy, sends email, posts to Slack
       ↓
    QA Agent        → Reviews everything and posts feedback on GitHub
```

---

## Agents

| Agent | What It Does |
|-------|-------------|
| **CEO Agent** | Breaks startup idea into tasks for each agent. Reviews product spec and requests revisions if needed. |
| **Product Agent** | Generates value proposition, user personas, features, and user stories. |
| **Engineer Agent** | Writes an HTML landing page and pushes it to GitHub via a Pull Request. |
| **Marketing Agent** | Generates tagline, email copy, tweet, LinkedIn and Instagram posts. Sends email via SendGrid and posts to Slack. |
| **QA Agent** | Reviews HTML and marketing copy against the product spec. Posts review comment on the GitHub PR. |

---

## Tech Stack

- **AI Model** — Groq (llama-3.3-70b-versatile) — Free
- **Email** — SendGrid
- **Notifications** — Slack
- **Code & Landing Page** — GitHub (branch + PR)
- **Language** — Python 3.10+

---

## Prerequisites

Before running, make sure you have accounts and API keys for:

| Service | Where to Get Key |
|---------|-----------------|
| Groq | console.groq.com |
| GitHub | github.com → Settings → Developer Settings → Personal Access Tokens |
| SendGrid | sendgrid.com |
| Slack | api.slack.com/apps |

---

## Setup Instructions

### Step 1 — Clone or Download the Project
```
cd your-project-folder
```

### Step 2 — Create Virtual Environment
```
python -m venv venv
```

### Step 3 — Activate Virtual Environment

Windows:
```
.\venv\Scripts\activate
```

Mac/Linux:
```
source venv/bin/activate
```

### Step 4 — Install Dependencies
```
pip install -r requirements.txt
pip install groq
```

### Step 5 — Create .env File
Copy the example file:
```
copy .env.example .env
```

Open and fill in all keys:
```
notepad .env
```

---

## Environment Variables

Fill in your `.env` file with all these keys:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxx
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxx
GITHUB_REPO=yourusername/your-repo-name
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxx
SLACK_CHANNEL=#your-channel-name
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxx
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=your@email.com
TEST_EMAIL=recipient@email.com
```

---

## Running the Project

```
python main.py
```

### Expected Output:
```
🚀 LAUNCHMIND MULTI-AGENT SYSTEM STARTING
✅ CEO decomposed idea into tasks
📦 Product spec created
⚙️ Engineer Agent generating HTML landing page...
✅ Engineer done! PR: https://github.com/your-repo/pull/1
📣 Marketing Agent generating copy...
✅ Email sent successfully!
✅ Slack message posted!
🔍 QA Verdict: PASS
✅ QA comment posted on GitHub PR
```

---

## Project Structure

```
launchmind/
│
├── agents/
│   ├── ceo_agent.py          # CEO — decomposes idea, reviews spec
│   ├── product_agent.py      # Product Manager — creates spec
│   ├── engineer_agent.py     # Engineer — builds landing page + GitHub PR
│   ├── marketing_agent.py    # Marketer — copy, email, Slack
│   └── qa_agent.py           # QA — reviews and posts on GitHub
│
├── message_bus.py            # Handles communication between agents
├── main.py                   # Entry point — runs all agents in order
├── requirements.txt          # Python dependencies
├── .env.example              # Template for environment variables
└── README.md                 # This file
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `GROQ_API_KEY not found` | Make sure .env file is in the project root folder |
| `channel_not_found` | Check SLACK_CHANNEL in .env matches your actual channel name |
| `JSONDecodeError` | The AI returned bad JSON — just run again, it retries automatically |
| `Branch already exists` | Delete the `agent-landing-page` branch on GitHub and run again |
| `401 Unauthorized GitHub` | Your GitHub token expired — create a new one |

---

## Notes

- The startup idea is defined in `main.py` — change the `STARTUP_IDEA` variable to test with your own idea
- Each full run creates a new GitHub issue and Pull Request
- If the branch `agent-landing-page` already exists on GitHub, delete it before running again
- Groq free tier supports up to 1,500 requests/day — more than enough for testing

