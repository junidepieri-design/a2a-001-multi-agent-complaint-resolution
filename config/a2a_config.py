# a2a_config.py
# Central configuration for the orchestrator and the domain agents.
# Adding a new domain agent means adding its URL here, nothing else.

import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Where each domain agent is reachable.
# The orchestrator reads the agent card from each URL to discover
# what that agent can do. Adding an agent is adding a line here.
AGENT_REGISTRY = {
    'transactions': 'http://localhost:8001',
    'complaints': 'http://localhost:8002'
}

# The orchestrator decides who to delegate to and consolidates the
# answers, so it gets the stronger model. Domain agents only pick a
# tool and format the result, which a smaller model handles fine.
ORCHESTRATOR_MODEL = 'claude-sonnet-4-6'
DOMAIN_AGENT_MODEL = 'claude-haiku-4-5-20251001'

MAX_TOKENS = 2048

# How many rounds of delegation the orchestrator is allowed before
# giving up. Prevents an infinite loop of agents calling each other.
MAX_DELEGATION_ROUNDS = 5

# How many tool rounds each domain agent is allowed internally.
MAX_TOOL_ROUNDS = 5

DATABASE_PATH = 'data/demo.db'

REQUEST_TIMEOUT = 60
