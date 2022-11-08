import argparse
import json
import re
import sys
import os
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
    
    list_issue_id: List[Dict[str, Any]] = []
    list_issue_id.append({'start': []})
    id_issue: str   
    for message in message_list:
        id_issue_list = re.findall(r"STEAPP-\d{1,3}", message)
        if id_issue_list == []:
            id_issue = ""
        else:    
            id_issue = id_issue_list[0]
        
        iter_counter = 0
        mismatch_counter = 0
        for index, dict_issue in enumerate(list_issue_id):
            iter_counter += 1
            if id_issue in dict_issue.values():
                list_issue_id[index]['message'].append(message)
                continue
            else:
                mismatch_counter += 1
                
        if iter_counter == mismatch_counter:
            message_for_list = [] 
            message_for_list.append(message)
            dict_issue_id: Dict[str, Any] = {'issue_key': id_issue, 'message': message_for_list}
            list_issue_id.append(dict_issue_id)
    
    list_issue_id.remove({'start': []})
        
    for count, dict_info in enumerate(list_issue_id):
        issue_key = dict_info['issue_key']   
        try:
            if issue_key != "":
                issue = client.issues[issue_key]
                client.users
                list_issue_id[count]['issue_summary'] = issue.summary
            else:
                list_issue_id[count]['issue_summary'] = ""
        except NotFound:
            pass
    
    fd = sys.stdout.fileno()
    data = json.dumps(list_issue_id).encode()
    while data:
        try:
            ret = os.write(fd, data)
        except OSError:
            continue
        data = data[ret:]
            
    return list_issue_id    
        

if __name__ == '__main__':
    main()
