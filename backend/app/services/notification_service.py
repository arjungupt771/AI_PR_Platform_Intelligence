"""
Slack + Discord notification service.
Posts review summaries after each PR is processed.
"""
import httpx
from typing import Optional, Dict
from app.core.config import settings


SEVERITY_EMOJI = {
    "critical": "🔴",
    "warning": "🟡",
    "suggestion": "🔵",
    "info": "⚪",
}

RISK_EMOJI = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🔴",
    "critical": "🚨",
}


def _build_slack_blocks(review_data: Dict) -> list:
    pr = review_data["pr"]
    review = review_data["review"]
    score = review.get("overall_score")
    issues = review.get("issues", [])
    security = review.get("security_flags", [])
    risk = review_data.get("risk_level", "unknown")
    consensus = review.get("consensus_agreement")
    model_breakdown = review.get("model_breakdown", [])

    critical = sum(1 for i in issues if i.get("severity") == "critical")
    warning = sum(1 for i in issues if i.get("severity") == "warning")
    suggestion = sum(1 for i in issues if i.get("severity") == "suggestion")

    score_str = f"{score:.1f}/10" if score is not None else "—"
    score_emoji = "🟢" if (score or 0) >= 7 else "🟡" if (score or 0) >= 5 else "🔴"

    # Multi-model breakdown text
    model_text = ""
    if model_breakdown:
        lines = []
        for m in model_breakdown:
            lines.append(f"• {m['provider'].upper()}: {m.get('score', '—'):.1f}/10 | {m.get('critical_count', 0)} critical")
        model_text = "\n".join(lines)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🔍 PR Review: #{pr['number']} {pr['title'][:60]}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Repo:*\n{pr['repo']}"},
                {"type": "mrkdwn", "text": f"*Author:*\n{pr['author']}"},
                {"type": "mrkdwn", "text": f"*Score:*\n{score_emoji} {score_str}"},
                {"type": "mrkdwn", "text": f"*Risk:*\n{RISK_EMOJI.get(risk, '⚪')} {risk.upper()}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Issues Found:*\n"
                    f"{SEVERITY_EMOJI['critical']} Critical: *{critical}*  "
                    f"{SEVERITY_EMOJI['warning']} Warnings: *{warning}*  "
                    f"{SEVERITY_EMOJI['suggestion']} Suggestions: *{suggestion}*"
                    + (f"\n{SEVERITY_EMOJI['critical']} Security flags: *{len(security)}*" if security else "")
                ),
            },
        },
    ]

    if model_breakdown and consensus is not None:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Multi-LLM Consensus ({consensus}% agreement):*\n{model_text}",
            },
        })

    if pr.get("url"):
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Full Review"},
                    "url": pr["url"],
                    "style": "primary",
                }
            ],
        })

    return blocks


def _build_discord_embed(review_data: Dict) -> Dict:
    pr = review_data["pr"]
    review = review_data["review"]
    score = review.get("overall_score")
    issues = review.get("issues", [])
    risk = review_data.get("risk_level", "unknown")
    model_breakdown = review.get("model_breakdown", [])

    critical = sum(1 for i in issues if i.get("severity") == "critical")
    warning = sum(1 for i in issues if i.get("severity") == "warning")
    suggestion = sum(1 for i in issues if i.get("severity") == "suggestion")

    color = 0x22c55e if (score or 0) >= 7 else 0xf59e0b if (score or 0) >= 5 else 0xef4444

    fields = [
        {"name": "📦 Repo", "value": pr["repo"], "inline": True},
        {"name": "👤 Author", "value": pr["author"], "inline": True},
        {"name": "📊 Score", "value": f"{score:.1f}/10" if score else "—", "inline": True},
        {"name": "⚠️ Risk", "value": f"{RISK_EMOJI.get(risk, '')} {risk.upper()}", "inline": True},
        {
            "name": "🔍 Issues",
            "value": f"🔴 {critical} critical | 🟡 {warning} warnings | 🔵 {suggestion} suggestions",
            "inline": False,
        },
    ]

    if model_breakdown:
        model_lines = "\n".join(
            f"• **{m['provider'].upper()}**: {m.get('score', 0):.1f}/10 | {m.get('critical_count', 0)} critical"
            for m in model_breakdown
        )
        fields.append({
            "name": f"🤖 Multi-LLM Breakdown ({review.get('consensus_agreement', 0)}% consensus)",
            "value": model_lines,
            "inline": False,
        })

    return {
        "title": f"PR #{pr['number']}: {pr['title'][:100]}",
        "url": pr.get("url", ""),
        "color": color,
        "fields": fields,
        "footer": {"text": "AI PR Intelligence Platform"},
    }


async def send_review_notification(
    pr_number: int,
    pr_title: str,
    pr_author: str,
    pr_url: Optional[str],
    repo_name: str,
    review: Dict,
    risk_level: str,
    app_url: str = "http://localhost:3000",
):
    """Send review notification to Slack and/or Discord."""
    if not settings.slack_bot_token and not settings.discord_webhook_url:
        return

    review_data = {
        "pr": {
            "number": pr_number,
            "title": pr_title,
            "author": pr_author,
            "url": pr_url or app_url,
            "repo": repo_name,
        },
        "review": review,
        "risk_level": risk_level,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        # ── Slack ────────────────────────────────────────────────────────────
        if settings.slack_bot_token and settings.slack_channel_id:
            try:
                await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {settings.slack_bot_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "channel": settings.slack_channel_id,
                        "blocks": _build_slack_blocks(review_data),
                        "text": f"PR #{pr_number} reviewed — score: {review.get('overall_score', '?')}/10",
                    },
                )
            except Exception as e:
                print(f"Slack notification failed: {e}")

        # ── Discord ──────────────────────────────────────────────────────────
        if settings.discord_webhook_url:
            try:
                await client.post(
                    settings.discord_webhook_url,
                    json={"embeds": [_build_discord_embed(review_data)]},
                )
            except Exception as e:
                print(f"Discord notification failed: {e}")
