from __future__ import annotations

import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

from body_profile import BodyProfile
from yield_engine import YieldEstimate

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_MODEL: str = "claude-haiku-4-5-20251001"
_MAX_TOKENS: int = 400
_TIMEOUT_S: float = 15.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_design_suggestions(
    garment_type: str,
    yield_est: YieldEstimate,
    body: BodyProfile,
) -> str | None:
    """Return suggestion text from Claude, or None on any failure.

    API key is loaded from the ``ANTHROPIC_API_KEY`` environment variable.
    If the key is absent or the API call fails for any reason, returns None
    so callers can degrade gracefully without blocking pattern generation.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    prompt = (
        f"You are a creative garment-making advisor. "
        f"The maker has a piece of woven fabric approximately "
        f"{yield_est.width_cm:.0f} cm wide by {yield_est.length_cm:.0f} cm long "
        f"({yield_est.area_cm2:.0f} cm² total). "
        f"They want to make a {garment_type}. "
        f"Body measurements: waist {body.waist:.0f} cm, hip {body.hip:.0f} cm. "
        f"Give 2–3 concise, practical design suggestions that work within these fabric constraints. "
        f"No emojis. Plain text only."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=_TIMEOUT_S)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception:
        return None
