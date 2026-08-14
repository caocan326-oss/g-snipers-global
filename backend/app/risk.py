"""Monitor → execute risk tiers.

Public G-Snipers description (not proprietary code): monitoring finds issues;
execution applies them. Analysis and apply are separate steps.
Low-risk work can land as a workspace draft; high/critical live-site or
outbound actions need a human confirm first.
"""

from fastapi import HTTPException

LOW = "low"
HIGH = "high"
RISKS = {LOW, HIGH}

CRITICAL = "critical"
SEV_HIGH = "high"
SEV_LOW = "low"
SEVERITIES = {CRITICAL, SEV_HIGH, SEV_LOW}

# Would change a live site or needs GSC / robots. Confirm required.
CRITICAL_CATEGORIES = {"schema", "index", "crawl", "canonical"}
HIGH_CATEGORIES = {"heading"}
HIGH_RISK_CATEGORIES = CRITICAL_CATEGORIES | {"distribution", "outreach_blast"}


def default_severity(category: str) -> str:
    if category in CRITICAL_CATEGORIES:
        return CRITICAL
    if category in HIGH_CATEGORIES:
        return SEV_HIGH
    return SEV_LOW


def severity_to_risk(severity: str) -> str:
    return HIGH if severity in {CRITICAL, SEV_HIGH} else LOW


def default_risk(category: str) -> str:
    return severity_to_risk(default_severity(category))


def needs_confirm(severity: str, risk: str) -> bool:
    return severity in {CRITICAL, SEV_HIGH} or risk == HIGH


def require_confirm(confirmed: bool, *, action: str) -> None:
    if not confirmed:
        raise HTTPException(status_code=400, detail=f"高风险动作「{action}」需要客户经理人工确认")
