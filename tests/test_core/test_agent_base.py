"""Tests for BaseAgent agentic loop."""
from unittest.mock import MagicMock

from src.core.agent_base import BaseAgent


class DummyAgent(BaseAgent):
    """Concrete agent for testing the base class."""

    def _register_tools(self):
        return [
            {
                "name": "echo",
                "description": "Echo back the input",
                "input_schema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            }
        ]

    def _build_system_prompt(self):
        return "You are a test agent."

    def _handle_tool_call(self, tool_name, tool_input):
        if tool_name == "echo":
            return f"Echo: {tool_input['text']}"
        return "Unknown tool"


def _make_response(stop_reason="end_turn", content=None, text="test result"):
    """Helper to create a mock Claude API response."""
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.usage = MagicMock()
    resp.usage.input_tokens = 100
    resp.usage.output_tokens = 50
    resp.usage.cache_read_input_tokens = 0
    resp.usage.cache_creation_input_tokens = 0

    if content is not None:
        resp.content = content
    else:
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text
        resp.content = [text_block]

    return resp


def test_agent_init():
    """Test agent initialization."""
    client = MagicMock()
    agent = DummyAgent(name="test", client=client)

    assert agent.name == "test"
    assert len(agent.tools) == 1
    assert agent.tools[0]["name"] == "echo"


def test_agent_process_simple(mock_anthropic_client):
    """Test simple process without tool calls."""
    mock_anthropic_client.messages.create.return_value = _make_response(
        text='{"result": "done"}'
    )

    agent = DummyAgent(name="test", client=mock_anthropic_client)
    result = agent.process({"input": "test"})

    assert result == {"result": "done"}
    mock_anthropic_client.messages.create.assert_called_once()


def test_agent_process_with_tool_call(mock_anthropic_client):
    """Test process with a tool call followed by final response."""
    # First response: tool call
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "echo"
    tool_block.input = {"text": "hello"}
    tool_block.id = "tool_123"

    first_response = _make_response(stop_reason="tool_use", content=[tool_block])

    # Second response: final text
    second_response = _make_response(text='{"echoed": "hello"}')

    mock_anthropic_client.messages.create.side_effect = [first_response, second_response]

    agent = DummyAgent(name="test", client=mock_anthropic_client)
    result = agent.process({"input": "test"})

    assert result == {"echoed": "hello"}
    assert mock_anthropic_client.messages.create.call_count == 2


def test_agent_process_max_iterations(mock_anthropic_client):
    """Test that process stops at max_iterations."""
    # Always return tool calls (never end_turn)
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "echo"
    tool_block.input = {"text": "loop"}
    tool_block.id = "tool_loop"

    response = _make_response(stop_reason="tool_use", content=[tool_block])
    mock_anthropic_client.messages.create.return_value = response

    agent = DummyAgent(name="test", client=mock_anthropic_client)
    result = agent.process({"input": "test"}, max_iterations=3)

    assert result["error"] == "Max iterations reached"
    assert result["partial"] is True
    assert mock_anthropic_client.messages.create.call_count == 3


def test_agent_handles_tool_error(mock_anthropic_client):
    """Test that tool errors are caught and returned to Claude."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "unknown_tool"
    tool_block.input = {}
    tool_block.id = "tool_err"

    first_response = _make_response(stop_reason="tool_use", content=[tool_block])
    second_response = _make_response(text='{"status": "handled error"}')

    mock_anthropic_client.messages.create.side_effect = [first_response, second_response]

    agent = DummyAgent(name="test", client=mock_anthropic_client)
    result = agent.process({"input": "test"})

    assert result == {"status": "handled error"}
