---
name: basic-agent
description: 'Run the Bini text agent for plain text or structured output tasks. Use when you need to call backend.ai.agents.text_agent.crew.text_agent, pass an optional JSON schema or Pydantic model, and validate the returned payload.'
argument-hint: 'Prompt to send to text_agent, plus optional schema output details'
user-invocable: true
disable-model-invocation: false
---

# Basic Agent

## When to Use
- Invoke the repository text agent for prompt-only tasks.
- Invoke the repository text agent with structured output requirements.
- Check whether a caller should pass a JSON schema dict or a Pydantic model.
- Validate that the agent returns a string for unstructured calls and validated JSON-compatible data for structured calls.

## Inputs
- A prompt string for `text_agent(prompt=...)`.
- Optional `schema_output` input as either a JSON schema dictionary or a `BaseModel` subclass.

## Procedure
1. Confirm the request maps to `text_agent` in [backend/ai/agents/text_agent/crew.py](../../../backend/ai/agents/text_agent/crew.py).
2. Determine whether the caller wants plain text or structured output.
3. For plain text, call `await text_agent(prompt)` and expect a string result.
4. For structured output, pass `schema_output` as either:
   - a `dict`, which the agent converts with `json_schema_to_pydantic()` before execution
   - a `BaseModel` subclass, which the agent uses directly
5. Treat execution as asynchronous. The function delegates blocking Crew execution through `asyncio.to_thread()`.
6. Validate the result shape:
   - without `schema_output`, the return value should be raw text
   - with `schema_output`, the return value should satisfy `validate_structured_output()`
7. If the call fails, inspect the logged exception from the `text-agent` logger and check whether the schema format matches the expected input type.

## Decision Points
- Use plain text mode when the caller only needs a natural-language response.
- Use structured mode when downstream code depends on stable keys and validated values.
- Use a Pydantic model for local Python callers that already own the schema type.
- Use a JSON schema dict for API-style inputs or dynamic schema definitions.

## Completion Criteria
- The prompt is routed through `text_agent`.
- Structured calls supply a valid schema input.
- The returned value matches the expected mode: `str` for plain text, `dict`-like validated output for structured tasks.
- Any failure includes enough context to distinguish execution errors from schema-conversion errors.

## Example Requests
- `/basic-agent Summarize this paragraph as plain text`
- `/basic-agent Extract title and sentiment using a JSON schema with required fields`
- `/basic-agent Show how to call text_agent from Python with a Pydantic response model`