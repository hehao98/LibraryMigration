import time
import logging
import pandas as pd
from github import Github
from util import get_tokens


def run():
    coding_data = []

    logging.info("Collecting commit coding data...")
    migrations = pd.read_excel("data/migrations.xlsx")
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

    logging.info("Collecting issue/PR coding data...")
    issues = pd.read_excel("data/issues.xlsx")
    tokens = get_tokens("tokens.txt")
    gh = Github(tokens[0])
    for idx, row in issues.iterrows():
        while True:
            try:
                logging.info("Collecting {} issue {}, remaining rate {}, reset at {}".format(
                    row["repoName"], row["number"], gh.rate_limiting, gh.rate_limiting_resettime))
                issue = gh.get_repo(row["repoName"]).get_issue(row["number"])
                data_type = "issue"
                link = "https://github.com/{}/issues/{}".format(row["repoName"], issue.number)
                if issue.pull_request is not None:
                    data_type = "pull request"
                    link = "https://github.com/{}/pull/{}".format(row["repoName"], issue.number)
                text = "{} - {} ({}) at {}\n\n{}\n\n".format(
                    issue.title, issue.user.name, issue.user.email, issue.created_at, issue.body)
                for comment in issue.get_comments():
                    text += "{} ({}) at {}: {}\n\n".format(
                        comment.user.name, comment.user.email, comment.created_at, comment.body)
                coding_data.append({
                    "type": data_type,
                    "link": link,
                    "text": text,
                })
                break
            except Exception as ex:
                logging.error("  {}".format(ex))
                sleep_time = gh.rate_limiting_resettime - time.time() + 10
                logging.info("  wait for {} seconds...".format(sleep_time))
                time.sleep(sleep_time)

    pd.DataFrame(coding_data).to_excel("data/coding.xlsx", index=False)
