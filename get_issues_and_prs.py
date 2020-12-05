import time
import pandas as pd
from github import Github, Issue
from github.GithubException import RateLimitExceededException


def get_tokens(token_file: str) -> list:
    with open(token_file, "r") as f:
        return list(x.strip() for x in f.readlines())


def issue_to_excel_row(issue: Issue, commit_sha: str) -> dict:
    return {
        "id": issue.id,
        "number": issue.number,
        "repoName": issue.repository.name,
        "related_commit": commit_sha,
        "url": "https://github.com/{}/issues/{}".format(issue.repository.full_name, issue.number),
        "api_url": issue.url,
        "title": issue.title
    }


if __name__ == "__main__":
    tokens = get_tokens("tokens.txt")
    print("GitHub tokens: {}".format(tokens))

    gh = Github(tokens[0])
    migrations = pd.read_excel("data/migrations.xlsx")
    commits = set(migrations["startCommit"]) | set(migrations["endCommit"])
    repo_names = set(map(lambda x: x.replace("_", "/"),  migrations["repoName"]))
    print("{} repositories, {} commits".format(len(repo_names), len(commits)))

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

    issue_list = []
    for commit in commits:
        print("Commit: {}".format(commit))
        while True:
            try:
                for issue in gh.search_issues("SHA:{}".format(commit)):
                    print("    {} {} {}".format(issue.id, issue.number, issue.repository.full_name, gh.rate_limiting))
                    issue_list.append(issue_to_excel_row(issue, commit))
                break
            except RateLimitExceededException as ex:
                print("    {}".format(ex))
                print("    wait for 60 seconds...")
                time.sleep(60)

    pd.DataFrame(issue_list).to_excel("data/issues.xlsx", index=False)
