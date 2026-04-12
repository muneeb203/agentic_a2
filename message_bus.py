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
