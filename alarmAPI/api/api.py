import ConfigParser
import argparse
import json

import MySQLdb
import os
from flask import Flask, request

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/setNumberLocation", methods=['PUT'])
def set_number_location():
    json_data = request.json.get('input')
    number = process_number(json_data.get('number'))
    if number == 'Wrong string':
        return create_response(json.dumps({'Error': 'Wrong string'}), 500)
    position = json_data.get('location')
    sql = (
        """update users set Position=%s where Number=%s""",(position, number))
    response = connect_to_database_return_sql_response(sql, False)
    if response[-1]:
        return create_response(json.dumps({'info': 'Data updated'}), 200)
    else:
        return create_response(json.dumps({'Error': 'Error retrieving numbers from SQL'}), 500)


@app.route("/getPoiTypeLocation/<type>", methods=['GET'])
def get_poi_locations(type):
    sql = (
        """select Longitude,Latitude from poi where Type=%s""",
        ([type]))
    response = connect_to_database_return_sql_response(sql)
    if response[-1]:
        list_of_positions = []
        for res in response[0]:
            position = {}
            position['longitude'] = res[0]
            position['latitude'] = res[1]
            list_of_positions.append(position)
        return create_response(json.dumps({'positions': list_of_positions}), 200)
    else:
        return create_response(json.dumps({'Error': 'Error retrieving numbers from SQL'}), 500)


@app.route("/getNumberLocation/<number>", methods=['GET'])
def get_number_location(number):
    number = process_number(number)
    sql = (
        """select Position from users where Number=%s""",
        ([number]))
    response = connect_to_database_return_sql_response(sql)
    if response[-1]:
        return create_response(json.dumps({'position': response[0]}), 200)
    else:
        return create_response(json.dumps({'Error': 'Error retrieving numbers from SQL'}), 500)


@app.route("/myRequests/<number>", methods=['GET'])
def check_database_for_user_access(number):
    number = process_number(number)
    sql = (
    """select number from users where ID IN (select Access_with from userAccess where user IN (select ID from users where Number=%s))""",
    ([number]))
    response = connect_to_database_return_sql_response(sql)
    if response[-1]:
        list_of_numbers = []
        for res in response[0]:
            list_of_numbers.append(process_number(res[0]))
        return create_response(json.dumps({'users': list_of_numbers}), 200)
    else:
        return create_response(json.dumps({'Error': 'Error retrieving numbers from SQL'}), 500)


@app.route("/whoWantsMe/<number>", methods=['GET'])
def check_database_for_pending_requests(number):
    number= process_number(number)
    sql = (
        """select Name, Number from users where ID IN (select user from userAccessPending where Access_with IN (select ID from users where Number=%s))""",
        ([number]))
    response = connect_to_database_return_sql_response(sql)
    if response[-1]:
        list_of_users = []
        for res in response[0]:
            map_of_users = {}
            map_of_users['number'] = process_number(res[1])
            map_of_users['name'] = res[0]
            list_of_users.append(map_of_users)
            print json.dumps({'users': list_of_users})
        return create_response(json.dumps({'users': list_of_users}), 200)
    else:
        return create_response(json.dumps({'Error': 'Error retrieving numbers from SQL'}), 500)

@app.route("/createUser", methods=['POST'])
def add_user():
    json_data = request.json.get('input')
    number = process_number(json_data.get('number'))
    if number == 'Wrong string':
        return create_response(json.dumps({'Error': 'Wrong string'}), 500)
    name = json_data.get('name')
    position = json_data.get('location')

    sql = ("""INSERT INTO users (Name, Number, Position) VALUES (%s, %s, %s)""", (name, number, position))
    response = connect_to_database_return_sql_response(sql, False)
    if response[-1]:
        return create_response(json.dumps({'info': 'success'}), 201)
    elif 'IntegrityError' in response[0][0]:
        return create_response(json.dumps({'Warning': 'User {} with number {} already exist'
                                          .format(name, number)}), 409)
    else:
        return create_response(json.dumps({'Error': 'Server Error with SQL processing'}), 500)


@app.route("/grantPermission", methods=['POST'])
def grant_permission():
    json_data = request.json.get('input')
    number = process_number(json_data.get('number'))
    my_umber = process_number(json_data.get('my-number'))
    sql = ("""DELETE from userAccessPending WHERE user IN (SELECT ID FROM users where Number=%s)""", ([number]))
    response = connect_to_database_return_sql_response(sql, False)
    sql = ("""INSERT INTO userAccess (user , Access_with) values ((SELECT ID from users where Number=%s), (SELECT ID from users where Number=%s))""", (number, my_umber))
    response = connect_to_database_return_sql_response(sql, False)
    sql = (
    """INSERT INTO userAccess (user , Access_with) values ((SELECT ID from users where Number=%s), (SELECT ID from users where Number=%s))""",
    (my_umber, number))
    response = connect_to_database_return_sql_response(sql, False)
    return create_response(json.dumps({'info': 'success'}), 200)


@app.route("/numberHasInstalled/<number>", methods=['GET'])
def get_number_user_has_app_installed_from_sql(number):
    """
    This function checks if user with given phone number <number>
    has application already installed.
    :param number: User phone number
    :return: 200 response with Success true if user has application
    installed or 404 reponse with success false if user does not have application
    installed
    """
    number = process_number(number)
    sql = ("""SELECT * FROM users WHERE Number=%s""", ([number]))
    result = connect_to_database_return_sql_response(sql)
    if not result[-1]:
        return result
    if len(result[0]) > 0:
        return create_response(json.dumps({'success': 'true'}), 200)
    else:
        return create_response(json.dumps({'success': 'false'}), 404)

    # disconnect from server


def process_number(number):
    number = number.replace(' ', '')
    if number.startswith('+421'):
        return number
    elif number.startswith('00421'):
        return '+{}'.format(number[2:])
    elif number.startswith('09'):
        return '+421{}'.format(number[1:])
    else:
        return 'Wrong string'


def create_response(json_object, response_code, content_type='application/json',
                    accept_type='application/json'):
    headers = {}
    if content_type:
        headers['ContentType'] = content_type
    if accept_type:
        headers['Accept'] = accept_type
    return json_object, response_code, headers


def connect_to_database_return_sql_response(sql_request, reading=True):
    db = MySQLdb.connect(dbHost, dbUser, dbPassword, dbName)

    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    sql = sql_request
    try:
        # Execute the SQL command
        cursor.execute(sql[0], (sql[1]))
        if reading:
            # Fetch all the rows in a list of lists.
            commit = cursor.fetchall()
        else:
            commit = db.commit()
        db.close()
        return commit, True
    except Exception as e:
        db.rollback()
        db.close()
        return create_response(json.dumps({'Error': 'Error: unable to fecth SQL data',
                                           'Error Message': repr(e)}), 500), False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-path', type=str,
                        default='../utility/config.ini',
                        help='Set path to config file')
    args = parser.parse_args()
    config_path = os.path.abspath('.') + '/' + args.config_path
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    global dbHost
    dbHost = config.get('API-Section', 'dbIp')
    global dbName
    dbName = config.get('API-Section', 'dbName')
    global dbUser
    dbUser = config.get('API-Section', 'dbUser')
    global dbPassword
    dbPassword = config.get('API-Section', 'dbPassword')

    ip = config.get('API-Section', 'ip')
    port = config.get('API-Section', 'port')
    app.run(ip, int(port))  # Open database connection
