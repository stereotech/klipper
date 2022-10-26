import argparse
import json
import re
import sys
from typing import List
from yandex_tracker_client import TrackerClient
from yandex_tracker_client.exceptions import NotFound
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    List
)

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
    
    list_issue_id: List[Dict[str, list]] = []   
    for message in message_list:
        #print(message)
        id_issue_list = re.findall(r"STEAPP-\d{1,3}", message)
        id_issue = id_issue_list[0]
        print(id_issue)
        
        id_check = False
        
        for index, dict_issue in enumerate(list_issue_id):
            message_for_list = [] 
            message_for_list.append(message)
            dict_issue_id: Dict[str, list] = {'issue_key': id_issue, 'message': message_for_list}
            if id_issue in dict_issue.values():
                list_issue_id[index]['message'].append(message)
                continue
            else:
                list_issue_id.append(dict_issue_id)
    
    for i in list_issue_id:
        print(i)
        
            
        # if id_check:
                   
        #         cur_mess_mass = []
        #         dict_issue_id = {'issue_key': id_issue, 'message': cur_mess_mass.append(message)}
        #     else:
        #         dict_issue_id['message'].append()
        
        

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