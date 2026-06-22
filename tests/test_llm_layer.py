from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from body_profile import BodyProfile
from yield_engine import YieldEstimate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def body() -> BodyProfile:
    return BodyProfile(
        bust=90.0,
        waist=72.0,
        hip=96.0,
        inseam=78.0,
        height=168.0,
        shoulder=38.0,
    )


@pytest.fixture()
def yield_est() -> YieldEstimate:
    return YieldEstimate(area_cm2=12000.0, width_cm=60.0, length_cm=100.0)


def _mock_anthropic_client(text: str = "Try a wrap skirt.") -> MagicMock:
    """Return a mock anthropic.Anthropic() client whose messages.create returns *text*."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


# ---------------------------------------------------------------------------
# Test 1: Returns a string when API succeeds
# ---------------------------------------------------------------------------

def test_returns_string_on_success(body: BodyProfile, yield_est: YieldEstimate) -> None:
    """get_design_suggestions returns a non-empty string when the API call succeeds."""
    from llm_layer import get_design_suggestions

    mock_client = _mock_anthropic_client("Try a wrap skirt.")

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
        with patch("llm_layer.anthropic.Anthropic", return_value=mock_client):
            result = get_design_suggestions("skirt", yield_est, body)

    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Test 2: Returns None when API key is absent
# ---------------------------------------------------------------------------

def test_returns_none_when_api_key_absent(body: BodyProfile, yield_est: YieldEstimate) -> None:
    """get_design_suggestions returns None when ANTHROPIC_API_KEY is not set."""
    from llm_layer import get_design_suggestions

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        result = get_design_suggestions("skirt", yield_est, body)

    assert result is None


# ---------------------------------------------------------------------------
# Test 3: Returns None when API call raises an exception
# ---------------------------------------------------------------------------

def test_returns_none_on_api_exception(body: BodyProfile, yield_est: YieldEstimate) -> None:
    """get_design_suggestions returns None when the API call raises any exception."""
    from llm_layer import get_design_suggestions

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("network error")

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
        with patch("llm_layer.anthropic.Anthropic", return_value=mock_client):
            result = get_design_suggestions("skirt", yield_est, body)

    assert result is None


# ---------------------------------------------------------------------------
# Test 4: Prompt includes required context fields
# ---------------------------------------------------------------------------

def test_prompt_contains_required_fields(body: BodyProfile, yield_est: YieldEstimate) -> None:
    """The prompt sent to Claude includes yield dimensions, body measurements, and garment type."""
    from llm_layer import get_design_suggestions

    mock_client = _mock_anthropic_client()

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
        with patch("llm_layer.anthropic.Anthropic", return_value=mock_client):
            get_design_suggestions("trousers", yield_est, body)

    call_kwargs = mock_client.messages.create.call_args
    prompt_text: str = call_kwargs.kwargs["messages"][0]["content"]

    assert "trousers" in prompt_text
    assert str(int(yield_est.width_cm)) in prompt_text
    assert str(int(yield_est.length_cm)) in prompt_text
    assert str(int(body.waist)) in prompt_text
    assert str(int(body.hip)) in prompt_text
