import ssl_fix  # Import SSL fix first

import anthropic
from typing import List, Optional, Dict, Any
import httpx

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Maximum number of tool calling rounds allowed per query
    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **Content Search Tool** - For searching within course materials and lessons
2. **Course Outline Tool** - For retrieving complete course structure and metadata

Tool Usage Guidelines:
- Use the **content search tool** for questions about specific course content or detailed educational materials
- Use the **course outline tool** for questions about course structure, lesson lists, or course metadata
- **You can use tools multiple times** to gather complete information before answering
- **Search iteratively**: If initial results are insufficient or you need to compare information, use tools again with refined parameters
- Example: First get a course outline to identify relevant lessons, then search specific lesson content for details
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course content questions**: Use content search tool (multiple times if needed), then answer
- **Course outline questions**: Use course outline tool to retrieve full course details (title, link, lesson list)
- **Multi-part questions**: Use tools sequentially to gather all needed information before answering
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

When returning course outlines, include:
- Course title
- Course link
- Complete lesson list with numbers and titles

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        # Create httpx client with SSL verification disabled
        http_client = httpx.Client(verify=False, timeout=60.0)
        self.client = anthropic.Anthropic(api_key=api_key, http_client=http_client)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to 2 sequential rounds of tool calling.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize message history
        messages = [{"role": "user", "content": query}]

        # Track tool calling rounds
        round_count = 0
        current_response = None

        # Tool calling loop - supports up to MAX_TOOL_ROUNDS rounds
        while round_count < self.MAX_TOOL_ROUNDS:
            # Prepare API call parameters
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Get response from Claude
            try:
                current_response = self.client.messages.create(**api_params)
            except Exception as e:
                return f"I encountered an error while processing your request: {str(e)}"

            # TERMINATION CONDITION 1: No tool use (Claude answered directly)
            if current_response.stop_reason != "tool_use":
                break

            # TERMINATION CONDITION 2: No tool_manager available
            if not tool_manager:
                return self._extract_text(current_response)

            # Execute tools and get results
            tool_results, execution_error = self._execute_all_tools(current_response, tool_manager)

            # TERMINATION CONDITION 3: Tool execution failure
            if execution_error:
                return self._handle_tool_error(current_response, execution_error)

            # Build message history for next round
            messages.append({"role": "assistant", "content": current_response.content})
            messages.append({"role": "user", "content": tool_results})

            round_count += 1
            # Loop continues for potential second round (TERMINATION CONDITION 4: max rounds)

        # If we exited loop due to max rounds and last response was tool_use,
        # make one more API call to get final answer
        if current_response and current_response.stop_reason == "tool_use" and round_count >= self.MAX_TOOL_ROUNDS:
            # Make final API call for Claude's answer (with tools still available)
            final_api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content
            }
            if tools:
                final_api_params["tools"] = tools
                final_api_params["tool_choice"] = {"type": "auto"}

            try:
                current_response = self.client.messages.create(**final_api_params)
            except Exception as e:
                return f"I encountered an error while generating final response: {str(e)}"

        # Extract and return final text response
        return self._extract_text(current_response)
    
    def _execute_all_tools(self, response, tool_manager):
        """
        Execute all tool calls from a response and collect results.

        Args:
            response: API response containing tool use requests
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (tool_results_list, error_message)
            - tool_results_list: List of tool result dicts for API
            - error_message: Error string if execution failed, None otherwise
        """
        tool_results = []

        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    # Execute the tool
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )

                    # Check if result indicates an error
                    if isinstance(tool_result, str) and (
                        tool_result.startswith("Error:") or tool_result.startswith("Tool")
                    ):
                        return None, f"Tool execution failed: {tool_result}"

                    # Add successful result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })

                except Exception as e:
                    return None, f"Tool execution exception: {str(e)}"

        return tool_results, None

    def _handle_tool_error(self, response, error_message: str) -> str:
        """
        Handle tool execution errors gracefully.

        Args:
            response: The API response that requested tools
            error_message: Description of the error

        Returns:
            User-friendly error message
        """
        # Try to extract any text content Claude provided before requesting tools
        text_blocks = [block for block in response.content if hasattr(block, 'text')]

        if text_blocks:
            return f"{text_blocks[0].text}\n\n[Note: Unable to complete search due to error: {error_message}]"

        # Fallback to generic error message
        return f"I encountered an error while searching: {error_message}"

    def _extract_text(self, response) -> str:
        """
        Extract text content from an API response.

        Args:
            response: API response object

        Returns:
            Text content from the response
        """
        if not response:
            return "I was unable to generate a response."

        # Find first text block in response content
        for content_block in response.content:
            if hasattr(content_block, 'text'):
                return content_block.text

        # Fallback if no text found
        return "I was unable to generate a text response."