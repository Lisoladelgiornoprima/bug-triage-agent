"""Base class for all agents with agentic loop implementation."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from anthropic import Anthropic
from loguru import logger


class BaseAgent(ABC):
    """Abstract base class for all specialist agents.

    Each agent:
    - Registers tools it can use (Claude function calling)
    - Defines its system prompt (role and behavior)
    - Implements tool execution logic
    - Runs an agentic loop (Claude calls tools -> execute -> return -> continue)
    """

    def __init__(self, name: str, client: Anthropic, model: str = "claude-sonnet-4-6"):
        self.name = name
        self.client = client
        self.model = model
        self.tools = self._register_tools()
        self.system_prompt = self._build_system_prompt()
        logger.info(f"Initialized {self.name} agent with {len(self.tools)} tools")

    @abstractmethod
    def _register_tools(self) -> List[Dict[str, Any]]:
        """Register tools this agent can use (Claude tool use schema).

        Returns:
            List of tool definitions in Anthropic tool use format.
        """
        pass

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """Build the system prompt defining this agent's role and behavior."""
        pass

    @abstractmethod
    def _handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool call and return the result.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result as a string
        """
        pass

    def _build_initial_messages(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build the initial message list from context.

        Subclasses can override to customize how context is presented.
        """
        context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
        return [
            {
                "role": "user",
                "content": f"Please analyze the following:\n\n{context_str}",
            }
        ]

    def _extract_result(self, response) -> Dict[str, Any]:
        """Extract the final result from Claude's response.

        Looks for text content in the response and attempts to parse
        JSON if present.
        """
        import json

        for block in response.content:
            if hasattr(block, "text"):
                text = block.text
                # Try to extract JSON from the response
                try:
                    # Look for JSON block in markdown
                    if "```json" in text:
                        json_str = text.split("```json")[1].split("```")[0].strip()
                        return json.loads(json_str)
                    # Try parsing the whole text as JSON
                    return json.loads(text)
                except (json.JSONDecodeError, IndexError):
                    return {"raw_response": text}
        return {"raw_response": "No text content in response"}

    def process(self, context: Dict[str, Any], max_iterations: int = 15) -> Dict[str, Any]:
        """Run the agentic loop.

        The loop continues until Claude stops calling tools (end_turn)
        or max_iterations is reached.
        """
        messages = self._build_initial_messages(context)
        logger.info(f"[{self.name}] Starting agentic loop")

        for iteration in range(max_iterations):
            logger.debug(f"[{self.name}] Iteration {iteration + 1}/{max_iterations}")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools if self.tools else None,
                messages=messages,
            )

            # If no tool use, agent is done
            if response.stop_reason == "end_turn":
                logger.info(f"[{self.name}] Completed in {iteration + 1} iterations")
                return self._extract_result(response)

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"[{self.name}] Calling tool: {block.name}")
                    try:
                        result = self._handle_tool_call(block.name, block.input)
                    except Exception as e:
                        logger.error(f"[{self.name}] Tool {block.name} failed: {e}")
                        result = f"Error: {e}"
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )

            # Append assistant response and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        logger.warning(f"[{self.name}] Reached max iterations ({max_iterations})")
        return {"error": "Max iterations reached", "partial": True}
