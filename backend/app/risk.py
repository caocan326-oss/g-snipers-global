"""Monitor → execute risk tiers.

Public G-Snipers description (not proprietary code): monitoring finds issues;
execution applies them. Low-risk work can land as a workspace draft; high-risk
live-site or outbound actions need a human confirm first.
"""

from fastapi import HTTPException

LOW = "low"
HIGH = "high"
RISKS = {LOW, HIGH}

# Categories that would change a live site or outbound channel.
HIGH_CATEGORIES = {"schema", "index", "crawl", "distribution", "outreach_blast"}


def default_risk(category: str) -> str:
    return HIGH if category in HIGH_CATEGORIES else LOW


def require_confirm(confirmed: bool, *, action: str) -> None:
    if not confirmed:
        raise HTTPException(status_code=400, detail=f"高风险动作「{action}」需要客户经理人工确认")
