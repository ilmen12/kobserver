from pathlib import Path


def test_skill_md_declares_kobserver_and_uv():
    text = Path("../SKILL.md").read_text(encoding="utf-8")
    assert "name: kobserver" in text
    assert '"bins": ["uv"]' in text
    assert "{baseDir}/scripts" in text
    assert "quotes" in text
    assert "chart" in text


def test_openai_yaml_exists():
    text = Path("../agents/openai.yaml").read_text(encoding="utf-8")
    assert 'display_name: "Kobserver"' in text
    assert "default_prompt:" in text
