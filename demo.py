# demo.py
# Runs the full case in the terminal, showing every delegation.
#
# Start both agents first:
#     uvicorn agents.transactions.server:app --port 8001
#     uvicorn agents.complaints.server:app --port 8002
#
# Then:
#     python demo.py
#     python demo.py "customer 1087 says a charge was refunded but never credited"

import logging
import sys

from orchestrator import agent
from orchestrator import a2a_client

logging.basicConfig(level=logging.WARNING)

DEFAULT_CASE = (
    'Customer 1042 says their statement has a charge of 49.90 '
    'they do not recognize.'
)


def show_discovery():
    # What the orchestrator learns before doing anything
    cards = a2a_client.discover_all()

    print('\nAGENT DISCOVERY')
    print('=' * 60)

    if not cards:
        print('  No agent reachable. Start the servers first:')
        print('    uvicorn agents.transactions.server:app --port 8001')
        print('    uvicorn agents.complaints.server:app --port 8002')
        return False

    for agent_name, card in cards.items():
        print(f'\n  {card["name"]}')
        print(f'  {card["description"][:70]}...')
        for skill in card.get('skills', []):
            print(f'    skill: {skill["name"]}')

    return True


def show_delegations(trace):
    # Every question the orchestrator sent and every answer it got
    print('\nDELEGATIONS')
    print('=' * 60)

    for index, step in enumerate(trace, 1):
        print(f'\n  [{index}] to {step["agent"]}')
        print(f'      asked:  {step["question"]}')
        print(f'      got:    {step["answer"][:300]}')


def run(customer_message):
    print('\nA2A MULTI AGENT DEMO')
    print('=' * 60)

    if not show_discovery():
        return

    print('\nCUSTOMER MESSAGE')
    print('=' * 60)
    print(f'  {customer_message}')

    trace = []
    final_answer = agent.resolve(customer_message, trace=trace)

    show_delegations(trace)

    print('\nCONSOLIDATED ANSWER')
    print('=' * 60)
    print(f'\n{final_answer}\n')

    print('=' * 60)
    print(f'{len(trace)} delegations, no database touched by the orchestrator.')


if __name__ == '__main__':
    message = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_CASE
    run(message)
