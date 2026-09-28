# target_agent

The Target Agent: the agent under attack.

Performs real tasks (email, calendar, file ops, web fetch) via tool calls using
LangGraph. Tool outputs (email bodies, web page content, file contents) are the
injection surface — the Attack Engine poisons these outputs to try to hijack the
agent's behavior away from the user's original task.

Contains the agent graph definition, tool definitions/mocks, and structured
logging of every tool call and model turn so the Eval Harness can reconstruct
what happened in a run.

## Contents

- `tools.py` — three mock tools (`read_email`, `read_file`, `fetch_url`),
  each backed by an in-memory fixture that is the injection surface.
- `llm.py` — the `LLMClient` interface the graph runs against, plus two
  implementations: `ScriptedLLM` (deterministic, no network/API — what the
  demo below uses) and `VLLMChatClient` (OpenAI-compatible client for the
  real vLLM server, wired up in build order step 6).
- `state.py` / `graph.py` — the LangGraph state and node wiring (agent
  decides an action, tools node executes it, loop until a final answer).
- `logging.py` — structlog config; every model turn and tool call is a
  structured JSON event.
- `run.py` — runs one demo task end-to-end.

## Run the demo

```bash
python3 -m target_agent.run
```

Prints one JSON log line per model turn / tool call for a task that reads
an email, cross-checks a file and a web page, and produces a final answer.
