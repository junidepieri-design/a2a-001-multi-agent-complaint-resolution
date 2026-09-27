# a2a_client.py
# Discovers remote agents by reading their agent cards, and sends them tasks.
#
# This is the only file that knows the A2A wire format. Swapping A2A for
# another protocol would mean rewriting this file and nothing else.

import logging
import uuid

import requests

from config.a2a_config import AGENT_REGISTRY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def discover(agent_url):
    '''
    Reads the agent card from a remote agent.
    The card is what tells the orchestrator what that agent can do,
    without exposing anything about how it does it.
    '''
    card_url = f'{agent_url}/.well-known/agent.json'
    response = requests.get(card_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def discover_all():
    '''
    Discovers every agent in the registry.
    Returns a dict of agent name to its card, skipping any agent
    that is not reachable so one agent being down does not break
    the whole orchestrator.
    '''
    discovered = {}

    for agent_name, agent_url in AGENT_REGISTRY.items():
        try:
            discovered[agent_name] = discover(agent_url)
            logger.info('discovered %s at %s', agent_name, agent_url)
        except Exception as error:
            logger.warning('could not reach %s at %s: %s', agent_name, agent_url, error)

    return discovered


def send_task(agent_name, question):
    '''
    Sends a task to a remote agent and returns its answer as plain text.
    The orchestrator sees only the answer, never the tools behind it.
    '''
    agent_url = AGENT_REGISTRY.get(agent_name)

    if agent_url is None:
        return f'Unknown agent: {agent_name}'

    payload = {
        'jsonrpc': '2.0',
        'id': str(uuid.uuid4()),
        'method': 'message/send',
        'params': {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': question}],
                'messageId': str(uuid.uuid4())
            }
        }
    }

    try:
        response = requests.post(agent_url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        body = response.json()
    except Exception as error:
        logger.exception('task to %s failed', agent_name)
        return f'The {agent_name} agent could not be reached: {error}'

    if 'error' in body:
        return f'The {agent_name} agent returned an error: {body["error"]}'

    parts = body.get('result', {}).get('parts', [])
    return ' '.join(
        part.get('text', '') for part in parts if part.get('kind') == 'text'
    ).strip()
