import pytest

from target_agent.tools import TOOLS, ToolError, tool_specs_for_llm


def test_read_email_returns_body():
    result = TOOLS["read_email"].run(message_id="msg-1")
    assert result["from"] == "alice@example.com"
    assert "docs/q3_plan.txt" in result["body"]


def test_read_email_missing_id_raises():
    with pytest.raises(ToolError):
        TOOLS["read_email"].run(message_id="does-not-exist")


def test_read_file_returns_content():
    result = TOOLS["read_file"].run(path="docs/q3_plan.txt")
    assert result["path"] == "docs/q3_plan.txt"
    assert "Q3 plan" in result["content"]


def test_fetch_url_returns_content():
    result = TOOLS["fetch_url"].run(url="https://intranet.example.com/roadmap")
    assert "Roadmap" in result["content"]


def test_tool_specs_for_llm_covers_all_tools():
    specs = tool_specs_for_llm()
    assert {spec["name"] for spec in specs} == set(TOOLS.keys())
    for spec in specs:
        assert spec["parameters"]["type"] == "object"
