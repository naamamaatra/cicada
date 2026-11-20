"""
SentinelOps AI — Design Taste UI Component Library.
Built with 'design-taste-frontend' anti-slop guidelines:
- High contrast, monolithic obsidian theme
- Strict 1px hairline borders with subtle top highlights
- Monospace typographic accents for telemetry IDs and metrics
- Clean status pills with luminous tints
"""

from typing import Dict, Any, List


def evaluate_metric_health(value: float, metric_type: str) -> str:
    """Evaluates individual metric according to hackathon thresholds."""
    if metric_type == "cpu":
        if value <= 50:
            return "EXCELLENT"
        elif value <= 70:
            return "GOOD"
        elif value <= 90:
            return "FAIR"
        else:
            return "POOR"

    elif metric_type in ("memory", "ram"):
        if value <= 60:
            return "EXCELLENT"
        elif value <= 75:
            return "GOOD"
        elif value <= 90:
            return "FAIR"
        else:
            return "POOR"

    elif metric_type == "latency_ms":
        if value <= 50:
            return "EXCELLENT"
        elif value <= 100:
            return "GOOD"
        elif value <= 250:
            return "FAIR"
        else:
            return "POOR"

    elif metric_type in ("packet_loss_pct", "packet_loss"):
        if value == 0:
            return "EXCELLENT"
        elif value <= 1.0:
            return "GOOD"
        elif value <= 5.0:
            return "FAIR"
        else:
            return "POOR"

    elif metric_type == "disk":
        if value <= 70:
            return "EXCELLENT"
        elif value <= 85:
            return "GOOD"
        elif value <= 95:
            return "FAIR"
        else:
            return "POOR"

    return "GOOD"


def calculate_overall_health(node_data: dict) -> str:
    """Calculates overall node health by evaluating the worst-case metric."""
    cpu_health = evaluate_metric_health(node_data.get("cpu", 0), "cpu")
    mem_health = evaluate_metric_health(node_data.get("memory", 0), "memory")
    lat_health = evaluate_metric_health(node_data.get("latency_ms", 0), "latency_ms")
    loss_health = evaluate_metric_health(node_data.get("packet_loss_pct", 0), "packet_loss_pct")
    disk_health = evaluate_metric_health(node_data.get("disk", 0), "disk")

    hierarchy = ["POOR", "FAIR", "GOOD", "EXCELLENT"]
    for state in hierarchy:
        if state in (cpu_health, mem_health, lat_health, loss_health, disk_health):
            return state
    return "EXCELLENT"


HEALTH_COLORS = {
    "EXCELLENT": "#10B981",  # Emerald Green
    "GOOD": "#3B82F6",       # Cobalt Blue
    "FAIR": "#F59E0B",       # Warm Amber
    "POOR": "#EF4444"        # Crimson Red
}

HEALTH_BADGES = {
    "EXCELLENT": "🟢 EXCELLENT",
    "GOOD": "🔵 GOOD",
    "FAIR": "🟡 FAIR",
    "POOR": "🔴 POOR"
}


# CSS System conforming to 'taste-skill' anti-slop rules
TASTE_SKILL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    /* Global canvas & typography */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #07080a !important;
        color: #e6edf3 !important;
    }

    /* Monospace elements */
    code, pre, .font-mono, .stJson {
        font-family: 'JetBrains Mono', ui-monospace, monospace !important;
    }

    /* Primary Card Architecture (Taste-Skill: one step off canvas, 1px border, hairline highlight) */
    .taste-card {
        background: #0f1218;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-top: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
        transition: transform 0.18s ease, border-color 0.18s ease;
    }
    .taste-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.15);
    }

    /* Hero / Status Bar Pill */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .status-pill-excellent {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #34d399;
    }
    .status-pill-good {
        background: rgba(59, 130, 246, 0.12);
        border: 1px solid rgba(59, 130, 246, 0.35);
        color: #60a5fa;
    }
    .status-pill-fair {
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.35);
        color: #fbbf24;
    }
    .status-pill-poor {
        background: rgba(239, 68, 68, 0.14);
        border: 1px solid rgba(239, 68, 68, 0.4);
        color: #f87171;
    }

    /* Phase 2: Privacy Inspector Boxes */
    .privacy-box-raw {
        background: #130f14;
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 12px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.84rem;
        color: #fca5a5;
    }
    .privacy-box-safe {
        background: #0d1512;
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 12px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.84rem;
        color: #6ee7b7;
    }

    /* Policy Allow-List Badges */
    .field-tag-allowed {
        display: inline-block;
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-family: 'JetBrains Mono', monospace;
        margin: 3px;
    }
    .field-tag-blocked {
        display: inline-block;
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.25);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-family: 'JetBrains Mono', monospace;
        text-decoration: line-through;
        margin: 3px;
    }

    /* Alert cards */
    .taste-alert-crit {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .taste-alert-warn {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }

    /* KPI stat block */
    .kpi-container {
        background: #0f1218;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: left;
    }
    .kpi-label {
        font-size: 0.76rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #8b949e;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #f0f3f8;
    }
</style>
"""
