import time
import logging
import pandas as pd
from github import Github, Issue
from util import get_tokens


def issue_to_excel_row(issue: Issue, commit_sha: str) -> dict:
    return {
        "id": issue.id,
        "number": issue.number,
        "repoName": issue.repository.name,
        "relatedCommit": commit_sha,
        "url": "https://github.com/{}/issues/{}".format(issue.repository.full_name, issue.number),
        "api_url": issue.url,
        "title": issue.title
    }


def run():
    tokens = get_tokens("tokens.txt")
    logging.info("GitHub tokens: {}".format(tokens))

    gh = Github(tokens[0])
    migrations = pd.read_excel("data/migrations.xlsx")
    commits = set(migrations["startCommit"]) | set(migrations["endCommit"])
    repo_names = set(map(lambda x: x.replace("_", "/"),  migrations["repoName"]))
    logging.info("{} repositories, {} commits".format(len(repo_names), len(commits)))

    """
    repos = dict()
    for repo_name in repo_names:
        repos[repo_name] = {
            "connection":  gh.get_repo(repo_name),
            "commits": set()
        }
    for repo_name, commit1, commit2 in zip(migrations["repoName"], migrations["startCommit"], migrations["endCommit"]):
        repos[repo_name]["commit"].update((commit1, commit2))
    """

    # Although it looks like we are retrieving issues, actually all we get are PRs!
    issue_list = []
    for idx, commit in enumerate(commits):
        logging.info("Commit {}/{}: {}".format(idx + 1, len(commits), commit))
        while True:
            try:
                for issue in gh.search_issues("SHA:{}".format(commit)):
                    logging.info("  {} {} {} {}".format(
                        issue.id, issue.number, issue.repository.full_name, gh.rate_limiting))
                    issue_list.append(issue_to_excel_row(issue, commit))
                break
            except Exception as ex:
                logging.error("  {}".format(ex))
                logging.info("  wait for 60 seconds...")
                time.sleep(60)

    pd.DataFrame(issue_list).to_excel("data/prs.xlsx", index=False)
