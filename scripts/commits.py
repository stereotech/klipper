import argparse


parser = argparse.ArgumentParser()
parser.add_argument(
    '-c', '--commits',
    metavar='commits',
    help="commits from github")
cmd_line_args = parser.parse_args()
commits = cmd_line_args.commits
with open(commits, "r") as f:
    for line in f:
        print(line)
# print(commits)