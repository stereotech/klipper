import argparse
import json
from yandex_tracker_client import TrackerClient
from yandex_tracker_client.exceptions import NotFound
import re

OAUTH_TOKEN = 'y0_AgAEA7qinHIPAAhewAAAAADNhpkJH-QqLI6uQRGPbD3H_oZIxtiICV0'
# iam_token = 't1.9euelZrMzoqQxo-LkM3JjJ3MipOYze3rnpWakZSXkI2OnI3NzZmPlsbOzZvl8_dpFkhn-e9GOwYP_t3z9ylFRWf570Y7Bg_-.oq21aVP0HwK9JyCB0IEqTqUxsVURpZOtJV5ExW86RYvZBHq8Ihy0cWj1RfM9Pl8djqLFcQTTZUPzK2qyFb5dBg'
ORG_ID = 70246

def main():
    
    client = TrackerClient(token=OAUTH_TOKEN, org_id=ORG_ID)
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--commits',
        metavar='commits',
        help="commits from github")
    cmd_line_args = parser.parse_args()
    commits_link = cmd_line_args.commits
    with open(commits_link, "r", encoding='utf-8') as f:
        commits = json.load(f)
    message_list = []
    list_issue_id = []
    for commit in commits:
        message = commit['message']
        message_list.append(message)
    for message in message_list:
        #print(message)
        id_issue = re.findall(r"STEAPP-\d{1,3}", message)
        print(id_issue)
        list_issue_id.append(id_issue)
        
    for issue_id in list_issue_id:    
        try:
            issue = client.issues[issue_id]
            client.users
            message_list.append(issue.summary)
        except NotFound:
            pass
    
    print(message_list)
        
    return message_list

if __name__ == '__main__':
    main()
# 
# for commit in commits:
#     print(commit)
    # dict_commit: Dict[str, Any]
    # dict_commit = commit
    # message = commit["message"]
    # message_list.append(message)
# print(message_list)
# dict_commits = json_commits[0]
# print(commits)