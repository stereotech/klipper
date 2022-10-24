import argparse
import json
from typing import (
    Dict,
    List,
    Any,
)

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
for message in message_list:
    print(message)
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