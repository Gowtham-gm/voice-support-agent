"""Mock customer-side operations (escalation ticketing, etc.)."""

_ESCALATION_LOG: list[dict] = []


def escalate_to_human(session_id: str, summary: str) -> dict:
    ticket_id = f"TCK-{len(_ESCALATION_LOG) + 1001}"
    ticket = {"ticket_id": ticket_id, "session_id": session_id, "summary": summary, "status": "open"}
    _ESCALATION_LOG.append(ticket)
    # In production: push to a ticketing system (Zendesk/Freshdesk) via API.
    return ticket
