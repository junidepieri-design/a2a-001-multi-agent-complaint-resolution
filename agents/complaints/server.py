# server.py
# A2A server for the complaints agent.
#
# Same shape as the transactions agent: an agent card for discovery
# and a task endpoint. The orchestrator talks to both the same way,
# without knowing anything about what is inside either one.
#
# Run:
#     uvicorn agents.complaints.server:app --port 8002

import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request

from agents.complaints.agent import answer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [complaints] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

CARD_PATH = Path(__file__).resolve().parent / 'agent_card.json'
AGENT_CARD = json.loads(CARD_PATH.read_text(encoding='utf-8'))

app = FastAPI(title='Complaints Agent')


@app.get('/.well-known/agent.json')
def agent_card():
    '''
    Serves the agent card. This is what makes the agent discoverable:
    any A2A client reads this to learn what the agent can do.
    '''
    return AGENT_CARD


@app.post('/')
async def handle_task(request: Request):
    '''
    Receives a task over JSON-RPC, runs the agent loop and returns the
    answer. The caller never sees which tools were used internally.
    '''
    body = await request.json()

    request_id = body.get('id')
    params = body.get('params', {})
    message = params.get('message', {})

    parts = message.get('parts', [])
    question = ' '.join(
        part.get('text', '') for part in parts if part.get('kind') == 'text'
    ).strip()

    if not question:
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {'code': -32602, 'message': 'No text part in message'}
        }

    logger.info('task received: %r', question)
    result = answer(question)
    logger.info('tools used: %s', result['tools_used'])

    return {
        'jsonrpc': '2.0',
        'id': request_id,
        'result': {
            'kind': 'message',
            'role': 'agent',
            'parts': [{'kind': 'text', 'text': result['answer']}]
        }
    }
