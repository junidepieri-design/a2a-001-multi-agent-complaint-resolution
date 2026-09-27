# tools.py
# Tools available to the transactions agent.
# Read only queries against the charges table, parameterized.

import sqlite3
from config.a2a_config import DATABASE_PATH


def connect():
    # One connection per call, the demo does not need pooling
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def find_charge(customer_id, amount=None, merchant=None):
    '''
    Finds a charge on a customer account, optionally narrowed by amount
    or merchant. Returns the most recent match with its full detail.
    '''
    query = 'SELECT * FROM charges WHERE customer_id = :customer_id'
    parameters = {'customer_id': customer_id}

    if amount is not None:
        query += ' AND amount = :amount'
        parameters['amount'] = amount

    if merchant:
        query += ' AND LOWER(merchant) LIKE :merchant'
        parameters['merchant'] = f'%{merchant.lower()}%'

    query += ' ORDER BY charge_date DESC'

    connection = connect()
    rows = connection.execute(query, parameters).fetchall()
    connection.close()

    if not rows:
        return {'found': False, 'message': 'No charge matched the criteria'}

    charges = [dict(row) for row in rows]

    return {
        'found': True,
        'match_count': len(charges),
        'most_recent': charges[0],
        'all_matches': charges
    }


def list_customer_charges(customer_id):
    '''
    Lists every charge on a customer account, most recent first.
    Used when the customer cannot specify which charge they question.
    '''
    connection = connect()
    rows = connection.execute(
        'SELECT * FROM charges WHERE customer_id = :customer_id ORDER BY charge_date DESC',
        {'customer_id': customer_id}
    ).fetchall()
    connection.close()

    if not rows:
        return {'found': False, 'message': 'No charges found for this customer'}

    return {
        'found': True,
        'charge_count': len(rows),
        'charges': [dict(row) for row in rows]
    }


# Tool definitions exposed to the model.
# The description is what the model reads to decide which one to call.
TOOL_DEFINITIONS = [
    {
        'name': 'find_charge',
        'description': (
            'Finds a specific charge on a customer account. Use this when the '
            'question mentions an amount, a merchant or a charge the customer '
            'does not recognize. Returns merchant, amount, date, whether the '
            'charge recurs, how many times it has occurred and whether it was '
            'already refunded.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'customer_id': {
                    'type': 'integer',
                    'description': 'The customer identifier'
                },
                'amount': {
                    'type': 'number',
                    'description': 'The charge amount, when the question mentions one'
                },
                'merchant': {
                    'type': 'string',
                    'description': 'The merchant name, when the question mentions one'
                }
            },
            'required': ['customer_id']
        }
    },
    {
        'name': 'list_customer_charges',
        'description': (
            'Lists every charge on a customer account. Use this when the '
            'question is general, or when find_charge returned nothing and you '
            'need to see what is actually on the account.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'customer_id': {
                    'type': 'integer',
                    'description': 'The customer identifier'
                }
            },
            'required': ['customer_id']
        }
    }
]

TOOL_FUNCTIONS = {
    'find_charge': find_charge,
    'list_customer_charges': list_customer_charges
}
