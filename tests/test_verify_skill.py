"""Keep the agent verification skill and its Claude mirror identical."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_verify_skill_mirrors_match() -> None:
    agents = (ROOT / ".agents/skills/verify/SKILL.md").read_text()
    claude = (ROOT / ".claude/skills/verify/SKILL.md").read_text()
    assert agents == claude
    assert "pytest-homeassistant-custom-component" in agents
    assert "scripts/verify.sh" in agents
