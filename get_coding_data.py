import pandas as pd
from github import Github, Issue
from util import get_tokens


def run():
    coding_data = []

    migrations = pd.read_excel("migrations.xlsx")
    commits = set()
    for idx, row in migrations.iterrows():
        if row["startCommit"] not in commits:
            coding_data.append({
                "type": "commit",
                "link": "https://github.com/{}/commit/{}".format(row["repoName"].replace("_", "/"), row["startCommit"]),
                "text": row["startCommitMessage"]
            })
        if row["endCommit"] not in commits:
            coding_data.append({
                "type": "commit",
                "link": "https://github.com/{}/commit/{}".format(row["repoName"].replace("_", "/"), row["endCommit"]),
                "text": row["endCommitMessage"]
            })
        commits.add(row["startCommit"])
        commits.add(row["endCommit"])

    issues = pd.read_excel("issues.xlsx")
    tokens = get_tokens("tokens.txt")
    gh = Github(tokens[0])
    for idx, row in issues.iterrows():
        issue = gh.get_repo(row["repoName"]).get_issue(row["number"])
        data_type = "issue"
        if issue.pull_request is not None:
            data_type = "pull request"
        text = "{} - {} ({}) at {}\n\n{}\n\n".format(
            issue.title, issue.user.name, issue.user.email,  issue.created_at, issue.body)
        for comment in issue.get_comments():
            text += "{} ({}) at {}: {}\n\n".format(
                comment.user.name, comment.user.email, comment.created_at, comment.body)
        coding_data.append({
            "type": data_type,
            "link": link,
            "text": text,
        })
