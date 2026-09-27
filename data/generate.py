# generate.py
# Creates the two demo databases, one per domain agent.
# Five records each, built to support the demo script end to end.
#
# Run once before starting the agents:
#     python -m data.generate

import os
import sqlite3

DATABASE_PATH = 'data/demo.db'


# Transactions the transactions agent can see.
# Customer 1042 has the StreamFlix charge the demo asks about.
CHARGES = [
    {
        'charge_id': 'CHG-8801',
        'customer_id': 1042,
        'amount': 49.90,
        'merchant': 'StreamFlix',
        'charge_date': '2026-09-12',
        'charge_type': 'recurring',
        'occurrence': 3,
        'refunded': 0
    },
    {
        'charge_id': 'CHG-8802',
        'customer_id': 1042,
        'amount': 49.90,
        'merchant': 'StreamFlix',
        'charge_date': '2026-08-12',
        'charge_type': 'recurring',
        'occurrence': 2,
        'refunded': 0
    },
    {
        'charge_id': 'CHG-8803',
        'customer_id': 1042,
        'amount': 132.40,
        'merchant': 'Metro Supermarket',
        'charge_date': '2026-09-08',
        'charge_type': 'single',
        'occurrence': 1,
        'refunded': 0
    },
    {
        'charge_id': 'CHG-8804',
        'customer_id': 1087,
        'amount': 19.90,
        'merchant': 'CloudBackup',
        'charge_date': '2026-09-03',
        'charge_type': 'recurring',
        'occurrence': 7,
        'refunded': 0
    },
    {
        'charge_id': 'CHG-8805',
        'customer_id': 1087,
        'amount': 89.00,
        'merchant': 'GymPass',
        'charge_date': '2026-09-01',
        'charge_type': 'recurring',
        'occurrence': 4,
        'refunded': 1
    }
]


# Complaint patterns the complaints agent can see.
# The StreamFlix pattern is what makes the demo answer complete.
COMPLAINTS = [
    {
        'pattern_id': 'PAT-201',
        'category': 'unrecognized_charge',
        'merchant': 'StreamFlix',
        'description': 'Customers do not recognize a recurring charge of 49.90',
        'root_cause': 'Free trial converted into a paid subscription without a clear reminder',
        'resolution': 'Cancel the recurring charge and refund the last two occurrences',
        'cases_last_30_days': 340,
        'resolution_rate': 0.94
    },
    {
        'pattern_id': 'PAT-202',
        'category': 'unrecognized_charge',
        'merchant': 'CloudBackup',
        'description': 'Customers do not recognize a recurring charge of 19.90',
        'root_cause': 'Subscription bundled with a device purchase',
        'resolution': 'Explain the bundle and offer cancellation for the next cycle',
        'cases_last_30_days': 58,
        'resolution_rate': 0.81
    },
    {
        'pattern_id': 'PAT-203',
        'category': 'duplicate_charge',
        'merchant': 'Metro Supermarket',
        'description': 'The same purchase appears twice on the statement',
        'root_cause': 'Card terminal retry after a network timeout',
        'resolution': 'Refund the duplicate within two business days',
        'cases_last_30_days': 112,
        'resolution_rate': 0.98
    },
    {
        'pattern_id': 'PAT-204',
        'category': 'refund_delay',
        'merchant': 'GymPass',
        'description': 'Refund approved but not credited to the statement',
        'root_cause': 'Refund settles on the next billing cycle',
        'resolution': 'Confirm the settlement date and set a follow up',
        'cases_last_30_days': 76,
        'resolution_rate': 0.89
    },
    {
        'pattern_id': 'PAT-205',
        'category': 'card_blocked',
        'merchant': None,
        'description': 'Card blocked after a purchase abroad',
        'root_cause': 'Fraud rule triggered without a prior travel notice',
        'resolution': 'Unblock the card and register the travel period',
        'cases_last_30_days': 203,
        'resolution_rate': 0.96
    }
]


def create_tables(connection):
    # Two tables, one per domain. Each agent only reads its own.
    cursor = connection.cursor()

    cursor.execute('DROP TABLE IF EXISTS charges')
    cursor.execute('''
        CREATE TABLE charges (
            charge_id    TEXT PRIMARY KEY,
            customer_id  INTEGER,
            amount       REAL,
            merchant     TEXT,
            charge_date  TEXT,
            charge_type  TEXT,
            occurrence   INTEGER,
            refunded     INTEGER
        )
    ''')

    cursor.execute('DROP TABLE IF EXISTS complaint_patterns')
    cursor.execute('''
        CREATE TABLE complaint_patterns (
            pattern_id          TEXT PRIMARY KEY,
            category            TEXT,
            merchant            TEXT,
            description         TEXT,
            root_cause          TEXT,
            resolution          TEXT,
            cases_last_30_days  INTEGER,
            resolution_rate     REAL
        )
    ''')

    connection.commit()
    print('  tables created')


def insert_charges(connection):
    # Populates the transactions domain
    cursor = connection.cursor()

    for charge in CHARGES:
        cursor.execute('''
            INSERT INTO charges VALUES (?,?,?,?,?,?,?,?)
        ''', (
            charge['charge_id'], charge['customer_id'], charge['amount'],
            charge['merchant'], charge['charge_date'], charge['charge_type'],
            charge['occurrence'], charge['refunded']
        ))

    connection.commit()
    print(f'  {len(CHARGES)} charges inserted')


def insert_complaints(connection):
    # Populates the complaints domain
    cursor = connection.cursor()

    for pattern in COMPLAINTS:
        cursor.execute('''
            INSERT INTO complaint_patterns VALUES (?,?,?,?,?,?,?,?)
        ''', (
            pattern['pattern_id'], pattern['category'], pattern['merchant'],
            pattern['description'], pattern['root_cause'], pattern['resolution'],
            pattern['cases_last_30_days'], pattern['resolution_rate']
        ))

    connection.commit()
    print(f'  {len(COMPLAINTS)} complaint patterns inserted')


def run():
    '''
    Creates the demo database with both domain tables.
    Data is intentionally small: what matters is the architecture,
    not the volume.
    '''
    print('\nGENERATING DEMO DATA')
    print('=' * 40)

    os.makedirs('data', exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)

    create_tables(connection)
    insert_charges(connection)
    insert_complaints(connection)

    connection.close()

    print(f'\nDatabase ready at {DATABASE_PATH}')
    print('=' * 40)


if __name__ == '__main__':
    run()
