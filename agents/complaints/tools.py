# tools.py
# Tools available to the complaints agent.
# Read only queries against the complaint patterns table, parameterized.

import sqlite3
from config.a2a_config import DATABASE_PATH


def connect():
    # One connection per call, the demo does not need pooling
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def match_pattern(description=None, merchant=None, category=None):
    '''
    Finds complaint patterns matching a description, a merchant or a
    category. Returns the root cause, the resolution applied before
    and how often that resolution worked.
    '''
    query = 'SELECT * FROM complaint_patterns WHERE 1 = 1'
    parameters = {}

    if merchant:
        query += ' AND LOWER(merchant) LIKE :merchant'
        parameters['merchant'] = f'%{merchant.lower()}%'

    if category:
        query += ' AND LOWER(category) LIKE :category'
        parameters['category'] = f'%{category.lower()}%'

    if description and not merchant and not category:
        query += ' AND LOWER(description) LIKE :description'
        parameters['description'] = f'%{description.lower()}%'

    query += ' ORDER BY cases_last_30_days DESC'

    connection = connect()
    rows = connection.execute(query, parameters).fetchall()
    connection.close()

    if not rows:
        return {
            'found': False,
            'message': 'No known pattern matched. This case needs individual handling.'
        }

    patterns = [dict(row) for row in rows]

    return {
        'found': True,
        'match_count': len(patterns),
        'best_match': patterns[0],
        'all_matches': patterns
    }


def get_pattern_volume(pattern_id):
    '''
    Returns how many cases of a pattern were recorded in the last
    thirty days, along with its resolution success rate.
    '''
    connection = connect()
    row = connection.execute(
        'SELECT * FROM complaint_patterns WHERE pattern_id = :pattern_id',
        {'pattern_id': pattern_id}
    ).fetchone()
    connection.close()

    if not row:
        return {'found': False, 'message': 'Pattern not found'}

    pattern = dict(row)

    # Volume is what separates an isolated incident from a systemic issue
    if pattern['cases_last_30_days'] >= 200:
        severity = 'systemic'
    elif pattern['cases_last_30_days'] >= 50:
        severity = 'recurring'
    else:
        severity = 'isolated'

    return {
        'found': True,
        'pattern_id': pattern['pattern_id'],
        'cases_last_30_days': pattern['cases_last_30_days'],
        'resolution_rate': pattern['resolution_rate'],
        'severity': severity
    }


# Tool definitions exposed to the model.
TOOL_DEFINITIONS = [
    {
        'name': 'match_pattern',
        'description': (
            'Searches known complaint patterns. Use this first, always. Pass '
            'the merchant when the complaint mentions one, otherwise pass the '
            'category or a description. Returns the root cause, the resolution '
            'that has been applied before and its success rate.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'description': {
                    'type': 'string',
                    'description': 'Plain language description of the complaint'
                },
                'merchant': {
                    'type': 'string',
                    'description': 'Merchant name, when the complaint mentions one'
                },
                'category': {
                    'type': 'string',
                    'description': (
                        'Complaint category, one of: unrecognized_charge, '
                        'duplicate_charge, refund_delay, card_blocked'
                    )
                }
            },
            'required': []
        }
    },
    {
        'name': 'get_pattern_volume',
        'description': (
            'Returns the case volume and severity of a pattern found by '
            'match_pattern. Use this to tell an isolated incident from a '
            'systemic issue, which changes how the case should be handled.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'pattern_id': {
                    'type': 'string',
                    'description': 'The pattern identifier returned by match_pattern'
                }
            },
            'required': ['pattern_id']
        }
    }
]

TOOL_FUNCTIONS = {
    'match_pattern': match_pattern,
    'get_pattern_volume': get_pattern_volume
}
