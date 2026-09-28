# target_agent

The Target Agent: the agent under attack.

Performs real tasks (email, calendar, file ops, web fetch) via tool calls using
LangGraph. Tool outputs (email bodies, web page content, file contents) are the
injection surface — the Attack Engine poisons these outputs to try to hijack the
agent's behavior away from the user's original task.

Contains the agent graph definition, tool definitions/mocks, and structured
logging of every tool call and model turn so the Eval Harness can reconstruct
what happened in a run.
