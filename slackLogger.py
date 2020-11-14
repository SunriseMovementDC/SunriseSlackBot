import requests
import time
import csv
import argparse

# karenID = 'U018BQLPLP8'
token = # removed for security


def apiGet(url, payload, pause=15):
    response = requests.get(url, params = payload).json()
    if response['ok']:
        return response
    elif response['error'] == 'ratelimited':
        print('waiting out rate-liminting: ', pause)
        time.sleep(pause)
        return apiGet(url, payload, pause * 2)
    else:
        print('ERROR: Unknown response.')
        print(response)
        exit(1)


def getLogins(payload):
    response = apiGet('https://slack.com/api/team.accessLogs', payload)
    return response['logins']


def getUserListPage(payload):
    response = apiGet("https://slack.com/api/users.list", payload)
    userList = response['members']
    cursor = None
    if 'response_metadata' in response:
        if 'next_cursor' in response['response_metadata']:
            cursor = response['response_metadata']['next_cursor']
    return (userList, cursor)


def getUserList(payload):
    userList = []
    cursor = 1
    while cursor:
        listPage = getUserListPage(payload)
        userList += listPage[0]
        cursor = listPage[1]
        payload['cursor'] = cursor
    return userList


def getUserLogs(datetime, minDatetime, filename, userID):
    print('current date: ', datetime)
    global token
    payload = {
        'token': token,
        'count': 1000,
        'before': datetime
    }
    logins = getLogins(payload)
    userLogs = []
    while datetime > minDatetime:
        for login in logins:
            if login["user_id"] == userID:
                if len(userLogs) == 0 or userLogs[-1]["date_first"] != login["date_first"]:
                    userLogs.append(login)
        datetime = logins[-1]["date_first"]
        payload["before"] = datetime + 1
        logins = getLogins(payload)
    headers = ["user_id", "username", "date_first", "date_last", "count", "ip", "user_agent", "isp", "country", "region"]
    extras = ["date_first_readable", "date_last_readable"]
    with open(filename, 'w') as csvfile:
        logWriter = csv.writer(csvfile)
        logWriter.writerow(headers + extras)
        for log in userLogs:
            data = []
            for header in headers:
                data.append(log[header])
            first = time.ctime(log["date_first"])
            last = time.ctime(log["date_last"])
            logWriter.writerow(data + [first, last])
    print("finished: ", filename)


def getUserStatuses(filename):
    global token
    payload = {
        'token': token,
        'limit': 200
    }
    userList = getUserList(payload)
    with open(filename, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter='|')
        writer.writerow(['Name', 'Status', 'StatusEmoji', 'Title', 'LastUpdated'])
        for user in userList:
            if user['deleted'] or user['is_bot']:
                continue
            data = []
            profile = user['profile']
            name = profile['display_name']
            if not name:
                if 'first_name' in profile:
                    name = profile['first_name']
                    if 'last_name' in profile:
                        if len(profile['last_name']) > 0:
                            name += ' ' + profile['last_name'][0]
            if not name:
                name = user['name']
            data.append(name)
            data.append(profile['status_text'])
            data.append(profile['status_emoji'])
            data.append(profile['title'])
            datetime = time.localtime(user['updated'])
            data.append(time.strftime('%Y-%m-%d %H:%M', datetime))
            if data[1] or data[2] or data[3]:
                writer.writerow(data)
    print('finished: ', filename)


def main():
    datetime = int(time.time())
    parser = argparse.ArgumentParser(description="A script to log data from the Sunrise DC slack workspace.")
    parser.add_argument("mode", help="The logging mode to use.")
    parser.add_argument("filename", help="The file to save results into")
    # 2020-05-01 00:00:00
    parser.add_argument("-d", "--minDatetime", type=int, default=1588291200, help="The start date to bound the search")
    parser.add_argument("-u", "--userID", help="The slack ID of the user to log")
    args = parser.parse_args()
    if (args.mode == "UserLog"):
        if not args.userID:
            print("ERROR: need a User ID")
            exit(1)
        getUserLogs(datetime, args.minDatetime, args.filename, args.userID)
    elif (args.mode == "UserStatus"):
        getUserStatuses(args.filename)

if __name__ == '__main__':
    main()