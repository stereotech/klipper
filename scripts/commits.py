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
commits = cmd_line_args.commits
with open(commits, "r") as f:
    commits = f.read()
json_commits = json.loads(commits)
message_list = []
for commit in json_commits:
    print(commit)
    # dict_commit: Dict[str, Any]
    # dict_commit = commit
    # message = commit["message"]
    # message_list.append(message)
# print(message_list)
# dict_commits = json_commits[0]
# print(commits)