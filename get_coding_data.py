import time
import logging
import asyncio
import pandas as pd
from github import Github
from github.GithubException import RateLimitExceededException
from util import get_tokens


async def get_issue(gh: Github, repo: str, number: int) -> dict or None:
    for i in range(0, 3):  # Max retry 3 times
        try:
            logging.info("Collecting {} issue {}, remaining rate {}, reset at {}".format(
                repo, number, gh.rate_limiting, gh.rate_limiting_resettime))
            issue = gh.get_repo(repo).get_issue(number)
            data_type = "issue"
            link = "https://github.com/{}/issues/{}".format(repo, issue.number)
            if issue.pull_request is not None:
                data_type = "pull request"
                link = "https://github.com/{}/pull/{}".format(repo, issue.number)
            text = "{} - {} ({}) at {}\n\n{}\n\n".format(
                issue.title, issue.user.name, issue.user.email, issue.created_at, issue.body)
            for comment in issue.get_comments():
                text += "{} ({}) at {}: {}\n\n".format(
                    comment.user.name, comment.user.email, comment.created_at, comment.body)
            return {
                "type": data_type,
                "link": link,
                "text": text,
            }
        except Exception as ex:
            logging.error("{}: {}".format(type(ex), ex))
            sleep_time = 5.0
            if type(ex) == RateLimitExceededException:
                sleep_time = gh.rate_limiting_resettime - time.time() + 10
                logging.info("  wait for {} seconds...".format(sleep_time))
            time.sleep(max(1.0, sleep_time))
    return None


async def async_run():
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
        commits.add(row["startCommit"])
        if row["endCommit"] not in commits:
            coding_data.append({
                "type": "commit",
                "link": "https://github.com/{}/commit/{}".format(row["repoName"].replace("_", "/"), row["endCommit"]),
                "text": row["endCommitMessage"]
            })
        commits.add(row["endCommit"])

    logging.info("Collecting issue/PR coding data...")
    issues = pd.read_excel("data/issues.xlsx")
    tokens = get_tokens("tokens.txt")
    ghs = [Github(tokens[i]) for i in range(len(tokens))]
    tasks = []
    for idx, row in issues.iterrows():
        tasks.append(get_issue(ghs[idx % len(ghs)], row["repoName"], row["number"]))
    coding_data.extend(filter(lambda x: x is not None, await asyncio.gather(*tasks)))

    pd.DataFrame(coding_data).to_excel("data/coding.xlsx", index=False)


def run():
    asyncio.run(async_run())
