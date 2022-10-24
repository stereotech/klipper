import argparse
import json
from yandex_tracker_client import TrackerClient
from yandex_tracker_client.exceptions import NotFound
import re
import sys

OAUTH_TOKEN = 'y0_AgAEA7qinHIPAAhewAAAAADNhpkJH-QqLI6uQRGPbD3H_oZIxtiICV0'
# iam_token = 't1.9euelZrMzoqQxo-LkM3JjJ3MipOYze3rnpWakZSXkI2OnI3NzZmPlsbOzZvl8_dpFkhn-e9GOwYP_t3z9ylFRWf570Y7Bg_-.oq21aVP0HwK9JyCB0IEqTqUxsVURpZOtJV5ExW86RYvZBHq8Ihy0cWj1RfM9Pl8djqLFcQTTZUPzK2qyFb5dBg'
ORG_ID = '70246'

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
    for commit in commits:
        message = commit['message']
        message_list.append(message)
    
    list_issue_id = []    
    for message in message_list:
        #print(message)
        id_issue_list = re.findall(r"STEAPP-\d{1,3}", message)
        id_issue = id_issue_list[0]
        print(id_issue)
        
        id_check = False
        for i in list_issue_id:
            dict_issue_id = {}
            if id_issue in i.values():
                id_check = True
                continue
            else:
                id_check = False
        # if id_check:
                   
        #         cur_mess_mass = []
        #         dict_issue_id = {'issue_key': id_issue, 'message': cur_mess_mass.append(message)}
        #     else:
        #         dict_issue_id['message'].append()
        
        list_issue_id.append(id_issue)
        
    for issue_id in list_issue_id:    
        try:
            issue = client.issues[issue_id]
            client.users
            message_dict = {''}
            message_list.append(issue.summary)
        except NotFound:
            pass
    
    print(message_list)
    
    fd = sys.stdout.fileno()
    data = {}    
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