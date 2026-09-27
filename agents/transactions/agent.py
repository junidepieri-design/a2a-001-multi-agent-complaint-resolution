# agent.py
# The transactions agent reasoning loop.
# Receives a question in plain language, picks tools, answers in plain language.

import json
import logging
from pathlib import Path

from anthropic import Anthropic

from agents.transactions.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from config.a2a_config import (
    ANTHROPIC_API_KEY,
    DOMAIN_AGENT_MODEL,
    MAX_TOKENS,
    MAX_TOOL_ROUNDS
)

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / 'prompts' / 'system.md'
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding='utf-8')

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def execute_tool(tool_name, tool_input):
    # Runs a tool and returns its result serialized for the model
    tool_function = TOOL_FUNCTIONS.get(tool_name)

    if tool_function is None:
        return json.dumps({'error': f'Unknown tool: {tool_name}'})

    try:
        result = tool_function(**tool_input)
        return json.dumps(result, default=str)
    except Exception as error:
        logger.exception('tool %s failed', tool_name)
        return json.dumps({'error': str(error)})


def answer(question):
    '''
    Answers a question from another agent about a customer account.
    Loops through tool calls until the model produces a text answer.
    '''
    messages = [{'role': 'user', 'content': question}]
    tools_used = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=DOMAIN_AGENT_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOL_DEFINITIONS
        )

        tool_use_blocks = [b for b in response.content if b.type == 'tool_use']

        if not tool_use_blocks:
            text_blocks = [b.text for b in response.content if b.type == 'text']
            final_answer = '\n'.join(text_blocks).strip()
            return {'answer': final_answer, 'tools_used': tools_used}

        messages.append({'role': 'assistant', 'content': response.content})

        tool_results = []
        for block in tool_use_blocks:
            logger.info('[transactions] tool: %s %s', block.name, dict(block.input))
            tools_used.append(block.name)

            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': execute_tool(block.name, dict(block.input))
            })

        messages.append({'role': 'user', 'content': tool_results})

    return {
        'answer': 'Could not complete the lookup within the allowed tool rounds.',
        'tools_used': tools_used
    }
