import json
import uuid
from datetime import datetime

# Shared inbox for all agents
message_bus = {
    "ceo": [],
    "product": [],
    "engineer": [],
    "marketing": [],
    "qa": []
}

message_log = []  # Records every message ever sent

_session_id = str(uuid.uuid4())
_session_start = datetime.utcnow().isoformat() + "Z"

def send_message(from_agent, to_agent, message_type, payload, parent_id=None):
    msg = {
        "message_id": str(uuid.uuid4()),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "parent_message_id": parent_id
    }
    message_bus[to_agent].append(msg)
    message_log.append(msg)
    print(f"\n📨 [{from_agent.upper()} → {to_agent.upper()}] Type: {message_type}")
    return msg["message_id"]

def get_messages(agent_name):
    msgs = message_bus[agent_name].copy()
    message_bus[agent_name] = []
    return msgs

def get_full_log():
    return message_log

def save_message_history(filepath="message_history.json"):
    """
    Persist the full message log to a JSON file.

    Schema
    ------
    {
      "session_id":   "<uuid>",           // unique per process run
      "session_start": "<ISO-8601>Z",     // when the session began
      "session_end":   "<ISO-8601>Z",     // when this function was called
      "total_messages": <int>,
      "agents": ["ceo", "product", ...],  // all agents that participated
      "messages": [
        {
          "message_id":        "<uuid>",
          "sequence":          <int>,      // 1-based position in the log
          "timestamp":         "<ISO-8601>Z",
          "from_agent":        "<str>",
          "to_agent":          "<str>",
          "message_type":      "<str>",
          "parent_message_id": "<uuid> | null",
          "payload":           { ... }
        },
        ...
      ]
    }
    """
    participants = sorted({
        agent
        for msg in message_log
        for agent in (msg["from_agent"], msg["to_agent"])
    })

    history = {
        "session_id": _session_id,
        "session_start": _session_start,
        "session_end": datetime.utcnow().isoformat() + "Z",
        "total_messages": len(message_log),
        "agents": participants,
        "messages": [
            {
                "message_id":        msg["message_id"],
                "sequence":          idx + 1,
                "timestamp":         msg["timestamp"],
                "from_agent":        msg["from_agent"],
                "to_agent":          msg["to_agent"],
                "message_type":      msg["message_type"],
                "parent_message_id": msg.get("parent_message_id"),
                "payload":           msg["payload"],
            }
            for idx, msg in enumerate(message_log)
        ],
    }

    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Message history saved → {filepath} ({len(message_log)} messages)")
