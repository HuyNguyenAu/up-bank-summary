import requests
import json
import sqlite3
import uuid
import logging

from os import path

database = 'budget.db'
api_key = '.api_key'


def get_transactions(date: str, api_key: str) -> list[dict[str, object]]:
    '''
    Gets a list of all transactions after the given settled `date`.
    '''

    if len(api_key) <= 0:
        logging.error('The parameter api_key must not be empty.')
        return []

    transactions = []
    # The link that will point to the next set of transactions.
    next_link = f'https://api.up.com.au/api/v1/transactions'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    params = {
        'filter[status]': 'SETTLED',
    }

    if len(date) > 0:
        params['filter[since]'] = date

    print('Fetching new transactions...')

    while True:
        # Get a list of transaction from Up Bank.
        response = requests.get(next_link, headers=headers, params=params)

        # Check if the request is successful.
        if response.status_code != 200:
            logging.error(
                f'Failed to get transactions. Status code {response.status_code}.')
            logging.error(response.content)
            return []

        content = json.loads(response.content)

        # Make sure there is the data key.
        if 'data' not in content:
            print('Failed to find data key in response.')
            return []

        # Go through the list of records and build up a list of transactions.
        for record in content['data']:
            # Get id of transaction.
            try:
                id = record['id']
            except:
                logging.error('Failed to find id of transaction.')
                continue

            # Get value of transaction.
            try:
                value = record['attributes']['amount']['value']
            except:
                logging.error(f'Failed to find value of {id} transaction.')
                continue

            # Get settled at date of transaction.
            try:
                settled_at = record['attributes']['settledAt']
            except:
                logging.error(
                    f'Failed to find settled at date of {id} transaction.')
                continue

            # Get description of transaction.
            try:
                description = record['attributes']['description']
            except:
                description = ''

            # Get category of transaction.
            try:
                category = record['relationships']['category']['data']['id']
            except:
                category = ''

            # Try to convert the id into a UUID.
            try:
                id = uuid.UUID(id)
            except:
                logging.error(f'Failed to convert {id} into UUID.')
                continue

            transactions.append({
                'id': id,
                'value': value,
                'description': description,
                'category': category,
                'settled_at': settled_at
            })

            logging.info(f'Found {str(id)} transaction.')

        # Make sure there is the links key.
        if 'links' not in content:
            return []

        # Get the next link.
        try:
            next_link = content['links']['next']

            # Stop when the next link is null.
            if next_link == None:
                break
        except:
            break

    print(f'Fetched {len(transactions)} new transactions.')
    return transactions


def insert_transactions(transactions: list[dict[str, object]]):
    '''
    Inserts given `transactions` into the `transactions` table.
    '''

    if len(transactions) <= 0:
        return

    try:
        # Open the database.
        connection = sqlite3.connect(database)
        cursor = connection.cursor()

        try:
            # Create table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id GUID PRIMARY KEY,
                value DOUBLE,
                description VARCHAR(255),
                category VARCHAR(255),
                settled_at DATETIME);
            ''')
        except:
            raise Exception('Failed to create transaction table.')

        # Insert transactions into transactions table.
        print('Saving new transactions...')
        count = 0
        for transaction in transactions:
            try:
                cursor.execute('''
                INSERT INTO transactions (id, value, description, category, settled_at) 
                VALUES (?, ?, ?, ?, ?);
                ''', (
                    transaction['id'],
                    transaction['value'],
                    transaction['description'],
                    transaction['category'],
                    transaction['settled_at'],
                ))
                count += 1
            except Exception as error:
                # This is a very crude way to quicky skip duplicate inserts.
                logging.error(
                    f'Failed to insert {transaction["id"]} into transactions table.')
                logging.error(str(error))
                continue
            logging.info(
                f'Inserted {transaction["id"]} into transactions table.')

        # Save the changes to transactions table.
        connection.commit()
        print(f'Saved {count} new transactions.')
    except Exception as error:
        # Not sure on how to handle SQLite errors.
        print(str(error))
    finally:
        connection.close()


def get_latest_settled_date() -> str:
    '''
    Get the latest settled at date from the `transactions` table.
    '''
    results = run_query(
        query='SELECT settled_at FROM transactions ORDER BY settled_at DESC LIMIT 1;',
        database=database,
        error_message='Failed to get latest settled date from transactions.')

    try:
        return results[0][0]
    except:
        return ''


def get_summmary():
    # Calculate the money going in and out for each account.
    # It would be nice if I can get the temp tables working.
    create_summary_query = '''
    DROP TABLE IF EXISTS money_in;
    DROP TABLE IF EXISTS money_out;

    CREATE TABLE money_in ([year] int, [month] VARCHAR[3], money_in DOUBLE);
    CREATE TABLE money_out ([year] int, [month] VARCHAR[3], money_out DOUBLE);

    INSERT INTO money_in ([year], [month], money_in)
	SELECT
		strftime('%Y', settled_at),
		CASE strftime('%m', settled_at)
			WHEN '01' THEN 'Jan'
			WHEN '02' THEN 'Feb'
			WHEN '03' THEN 'Mar'
			WHEN '04' THEN 'Apr'
			WHEN '05' THEN 'May'
			WHEN '06' THEN 'Jun'
			WHEN '07' THEN 'Jul'
			WHEN '08' THEN 'Aug'
			WHEN '09' THEN 'Sep'
			WHEN '10' THEN 'Oct'
			WHEN '11' THEN 'Nov'
			WHEN '12' THEN 'Dec'
			ELSE ''
		END,
		SUM(value)
	FROM transactions
	WHERE
		value > 0 AND
		description NOT LIKE 'Round Up' AND
		description NOT LIKE 'Auto Transfer from%' AND
		description NOT LIKE 'Auto Transfer to%' AND
		description NOT LIKE 'Transfer from%' AND
		description NOT LIKE 'Transfer to%' AND
		description NOT LIKE 'Forward from%' AND
		description NOT LIKE 'Forward to%' AND
		description NOT LIKE 'Cover from%' AND
		description NOT LIKE 'Cover to%' AND
		description NOT LIKE 'Quick save transfer from%' AND
		description NOT LIKE 'Quick save transfer to%' AND
		description NOT LIKE 'Interest'
	GROUP BY
		strftime('%Y', settled_at),
		strftime('%m', settled_at)
	ORDER BY strftime('%Y', settled_at) DESC, strftime('%m', settled_at) DESC;


    INSERT INTO money_out ([year], [month], money_out)
	SELECT
		strftime('%Y', settled_at),
		CASE strftime('%m', settled_at)
			WHEN '01' THEN 'Jan'
			WHEN '02' THEN 'Feb'
			WHEN '03' THEN 'Mar'
			WHEN '04' THEN 'Apr'
			WHEN '05' THEN 'May'
			WHEN '06' THEN 'Jun'
			WHEN '07' THEN 'Jul'
			WHEN '08' THEN 'Aug'
			WHEN '09' THEN 'Sep'
			WHEN '10' THEN 'Oct'
			WHEN '11' THEN 'Nov'
			WHEN '12' THEN 'Dec'
			ELSE ''
		END,
		SUM(value)
	FROM transactions
	WHERE
		value < 0 AND
		description NOT LIKE 'Round Up' AND
		description NOT LIKE 'Auto Transfer from%' AND
		description NOT LIKE 'Auto Transfer to%' AND
		description NOT LIKE 'Transfer from%' AND
		description NOT LIKE 'Transfer to%' AND
		description NOT LIKE 'Forward from%' AND
		description NOT LIKE 'Forward to%' AND
		description NOT LIKE 'Cover from%' AND
		description NOT LIKE 'Cover to%' AND
		description NOT LIKE 'Quick save transfer from%' AND
		description NOT LIKE 'Quick save transfer to%' AND
		description NOT LIKE 'Interest'
	GROUP BY
		strftime('%Y', settled_at),
		strftime('%m', settled_at)
	ORDER BY strftime('%Y', settled_at) DESC, strftime('%m', settled_at) DESC;
    '''
    # Join the money in and out tables together.
    get_summary_query = '''
    SELECT
	    money_in.[year],
	    money_in.[month],
	    IFNULL(money_in.money_in, 0) + IFNULL(money_out.money_out, 0) [money_saved],
	    IFNULL(money_in.money_in, 0) [money_in],
	    ABS(IFNULL(money_out.money_out, 0)) [money_out]
    FROM money_in
    LEFT JOIN money_out ON money_in.[year] = money_out.[year] AND money_in.[month] = money_out.[month];
    '''
    # Delete the tables after we are done.
    delete_summary_query = '''
    DROP TABLE IF EXISTS money_in;
    DROP TABLE IF EXISTS money_out;
    '''
    run_query(
        query=create_summary_query,
        database=database,
        error_message='Failed to create summary of transactions.',
        script=True)

    results = run_query(
        query=get_summary_query,
        database=database,
        error_message='Failed to get summary of transactions.',)

    run_query(
        query=delete_summary_query,
        database=database,
        error_message='Failed to delete summary of transactions.',
        script=True)

    # Print the results in a nice table. It would be handy to use an external library,
    # but today's challenge is to not use any external libraries.
    print('{:<6} {:<7} {:<13} {:<10} {:<11}'.format(
        'Year', 'Month', 'Money Saved', 'Money In', 'Money Out'))
    for row in results:
        print('{:<6} {:<7} {:<13} {:<10} {:<11}'.format(
            row[0], row[1], round(row[2], 2), round(row[3], 2), round(row[4], 2)))


def run_query(query: str, database: str, error_message: str, script: bool = False) -> list[object]:
    '''
    Run a query with the given `query` on the given `database`. Display
    the given `error_message` if the query fails.
    '''
    if len(query) <= 0:
        logging.error('The parameter query must not be empty.')
        return []

    if len(database) <= 0:
        logging.error('The database query must not be empty.')
        return []

    if len(error_message) <= 0:
        logging.error('The error_message query must not be empty.')
        return []

    results = []

    try:
        # Allow the SQLite database to insert UUID values.
        sqlite3.register_adapter(uuid.UUID, lambda u: u.bytes_le)

        # Open the database.
        connection = sqlite3.connect(database)
        cursor = connection.cursor()

        # Run the query and get the result.
        try:
            if script:
                results = cursor.executescript(query).fetchall()
            else:
                results = cursor.execute(query).fetchall()
        except Exception as error:
            logging.error(str(error))
            raise Exception(error_message)

    except Exception as error:
        # Not sure on how to handle SQLite errors.
        logging.error(str(error))
        logging.error('Failed to run query.')
    finally:
        connection.close()
    return results


def get_api_key() -> str:
    '''
    Return the api_key value in `.api_key` file.
    '''
    api_key_path = f'{path.dirname(path.realpath(__file__))}/{api_key}'

    try:
        # Make sure the api key file exists.
        if path.exists(api_key_path) and path.isfile(api_key_path):
            with open(api_key_path, 'r') as file:
                value = file.readline()

                # Check if the is anything in the file.
                if len(value) > 0:
                    return value

                logging.error(f'No api key found in {api_key_path}.')
                return ''
        raise Exception()

    except:
        logging.error(f'Failed to load {api_key_path}.')
    return ''


def main():
    # Enable logging.
    logging.basicConfig(
        format='%(asctime)s [%(filename)s:%(lineno)s] (%(levelname)s): %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        filename='budget.log',
        encoding='utf-8',
        level=logging.INFO
    )

    # Get new transactions.
    transactions = get_transactions(
        date=get_latest_settled_date(),
        api_key=get_api_key())
    insert_transactions(
        transactions=transactions)

    # Show the summary for each month.
    print('Getting summary...')
    get_summmary()


if __name__ == '__main__':
    main()
