import pytest

from target_agent.tools import TOOLS, ToolError, make_tools, tool_specs_for_llm


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


def test_make_tools_without_poison_matches_default_fixtures():
    clean = make_tools()
    assert clean["read_email"].run(message_id="msg-1") == TOOLS["read_email"].run(
        message_id="msg-1"
    )


def test_make_tools_poison_appends_to_target_fixture_only():
    poisoned = make_tools(poison={"msg-1": "INJECTED TEXT"})

    email = poisoned["read_email"].run(message_id="msg-1")
    assert "INJECTED TEXT" in email["body"]

    # Other fixtures stay clean.
    file_result = poisoned["read_file"].run(path="docs/q3_plan.txt")
    assert "INJECTED TEXT" not in file_result["content"]


def test_make_tools_poison_unknown_key_raises():
    with pytest.raises(ToolError):
        make_tools(poison={"no-such-key": "x"})


def test_make_tools_does_not_mutate_module_fixtures():
    make_tools(poison={"msg-1": "INJECTED TEXT"})
    clean = TOOLS["read_email"].run(message_id="msg-1")
    assert "INJECTED TEXT" not in clean["body"]
