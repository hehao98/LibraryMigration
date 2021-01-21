import time
import logging
import asyncio
import pandas as pd
from collections import defaultdict
from github import Github
from github.GithubException import RateLimitExceededException, UnknownObjectException
from ghutil import get_tokens, get_issues_in_text


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
        except RateLimitExceededException as ex:
            logging.error("{}: {}".format(type(ex), ex))
            sleep_time = gh.rate_limiting_resettime - time.time() + 10
            logging.info("  wait for {} seconds...".format(sleep_time))
            time.sleep(max(1.0, sleep_time))
        except UnknownObjectException as ex:
            logging.error("{}: {}".format(type(ex), ex))
            break
        except Exception as ex:
            logging.error("{}: {}".format(type(ex), ex))
            time.sleep(5)
    return None


async def get_coding_for_commits_and_prs():
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
    issues = pd.read_excel("data/prs.xlsx")
    tokens = get_tokens("tokens.txt")
    ghs = [Github(tokens[i]) for i in range(len(tokens))]
    tasks = []
    for idx, row in issues.iterrows():
        tasks.append(get_issue(ghs[idx % len(ghs)],
                               row["repoName"], row["number"]))
    coding_data.extend(filter(lambda x: x is not None, await asyncio.gather(*tasks)))

    pd.DataFrame(coding_data).to_excel(
        "data/coding_commits_prs.xlsx", index=False)
    return coding_data


async def get_coding_for_linked_issues():
    coding_issue = []

    coding_commit_pr = pd.read_excel("data/coding_commits_prs.xlsx").fillna("")
    issue_links = set()
    issues = []
    for idx, row in coding_commit_pr.iterrows():
        repo_name = row["link"].split("/")[3] + "/" + row["link"].split("/")[4]
        for name, number in get_issues_in_text(repo_name, row["text"]):
            issue_links.add((name, number))
            issues.append({
                "repoName": name,
                "number": number,
                "sourceLink": row["link"],
                "sourceRepoName": repo_name,
            })
    logging.info(
        "{} issues found in commit and PR coding text".format(
            len(issue_links)))
    pd.DataFrame(issues).to_excel("data/issues.xlsx", index=False)

    tokens = get_tokens("tokens.txt")
    ghs = [Github(tokens[i]) for i in range(len(tokens))]
    tasks = []
    for idx, (repo_name, number) in enumerate(issue_links):
        tasks.append(get_issue(ghs[idx % len(ghs)], repo_name, number))
    coding_issue.extend(filter(lambda x: x is not None, await asyncio.gather(*tasks)))

    pd.DataFrame(coding_issue).to_excel("data/coding_issues.xlsx", index=False)
    return coding_issue


def add_possible_migrations():
    data1 = pd.read_excel(
        "data/coding_issues.xlsx").drop_duplicates(["type", "link"]).fillna("")
    data2 = pd.read_excel(
        "data/coding_commits_prs.xlsx").drop_duplicates(["type", "link"]).fillna("")
    data = pd.concat([data1, data2])
    migrations = pd.read_excel("data/migrations.xlsx")
    issues = pd.read_excel("data/issues.xlsx")
    prs = pd.read_excel("data/prs.xlsx")

    link_to_migrations = defaultdict(set)
    for idx, row in migrations.iterrows():
        link_to_migrations[row["startCommit"]].add(
            (row["fromLib"], row["toLib"]))
        link_to_migrations[row["endCommit"]].add(
            (row["fromLib"], row["toLib"]))

    for idx, row in prs.iterrows():
        link_to_migrations[(row["repoName"], row["number"])] = set(
            link_to_migrations[row["relatedCommit"]])

    for idx, row in issues.iterrows():
        repo_name = row["sourceLink"].split(
            "/")[3] + "/" + row["sourceLink"].split("/")[4]
        number = row["sourceLink"].split("/")[6]
        if "commit" in row["sourceLink"]:
            link_to_migrations[(row["repoName"], row["number"])] = set(
                link_to_migrations[number])
        else:
            link_to_migrations[(row["repoName"], row["number"])] = set(
                link_to_migrations[(repo_name, int(number))])

    for idx, row in data.iterrows():
        repo_name = row["link"].split("/")[3] + "/" + row["link"].split("/")[4]
        number = row["link"].split("/")[6]
        if row["type"] == "commit":
            pairs = list(sorted(link_to_migrations[number]))
        else:
            pairs = list(sorted(link_to_migrations[(repo_name, int(number))]))
        data.loc[idx, "fromLib"] = "\n".join(x for x, y in pairs)
        data.loc[idx, "toLib"] = "\n".join(y for x, y in pairs)

    data.to_excel("data/coding.xlsx", index=False)


def run():
    asyncio.run(get_coding_for_commits_and_prs())
    asyncio.run(get_coding_for_linked_issues())
    add_possible_migrations()
