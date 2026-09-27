# agent.py
# The orchestrator. Talks to the customer, delegates to domain agents,
# consolidates the answers.
#
# It has no database access and no domain tools. Every tool it has is
# a delegation to another agent, built dynamically from the agent cards.

import json
import logging
from pathlib import Path

from anthropic import Anthropic

from orchestrator import a2a_client
from config.a2a_config import (
    ANTHROPIC_API_KEY,
    ORCHESTRATOR_MODEL,
    MAX_TOKENS,
    MAX_DELEGATION_ROUNDS
)

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / 'prompts' / 'system.md'
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding='utf-8')

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def build_delegation_tools(agent_cards):
    '''
    Turns each discovered agent into one delegation tool.
    The tool description is built from the agent card, so adding an
    agent to the registry is enough for the orchestrator to start
    using it. No code change here.
    '''
    tools = []

    for agent_name, card in agent_cards.items():
        skill_lines = '\n'.join(
            f'  {skill["name"]}: {skill["description"]}'
            for skill in card.get('skills', [])
        )

        tools.append({
            'name': f'ask_{agent_name}',
            'description': (
                f'{card["description"]}\n\n'
                f'What this agent can do:\n{skill_lines}\n\n'
                'Send a question in plain language, the way you would ask a '
                'colleague. Include the customer id when the question is about '
                'a specific account.'
            ),
            'input_schema': {
                'type': 'object',
                'properties': {
                    'question': {
                        'type': 'string',
                        'description': 'The question, in plain language'
                    }
                },
                'required': ['question']
            }
        })

    return tools


def resolve(customer_message, trace=None):
    '''
    Resolves a customer complaint by delegating to the domain agents
    and consolidating their answers into a single response.
    Pass a list as trace to collect what happened, for the demo output.
    '''
    agent_cards = a2a_client.discover_all()

    if not agent_cards:
        return 'No domain agent is reachable. Start the agent servers first.'

    delegation_tools = build_delegation_tools(agent_cards)
    messages = [{'role': 'user', 'content': customer_message}]

    for _ in range(MAX_DELEGATION_ROUNDS):
        response = client.messages.create(
            model=ORCHESTRATOR_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=delegation_tools
        )

        tool_use_blocks = [b for b in response.content if b.type == 'tool_use']

        if not tool_use_blocks:
            text_blocks = [b.text for b in response.content if b.type == 'text']
            return '\n'.join(text_blocks).strip()

        messages.append({'role': 'assistant', 'content': response.content})

        tool_results = []
        for block in tool_use_blocks:
            agent_name = block.name.replace('ask_', '')
            question = block.input['question']

            logger.info('delegating to %s: %r', agent_name, question)
            agent_answer = a2a_client.send_task(agent_name, question)

            if trace is not None:
                trace.append({
                    'agent': agent_name,
                    'question': question,
                    'answer': agent_answer
                })

            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': agent_answer
            })

        messages.append({'role': 'user', 'content': tool_results})

    return 'Could not resolve the case within the allowed delegation rounds.'
