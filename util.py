import os
import re
import logging
import pymongo
import pandas as pd
from collections import Counter, defaultdict
from typing import List, Tuple, Set, Iterable


MONGO_URL = "mongodb://127.0.0.1:27017"


def get_tokens(token_file: str) -> List[str]:
    """
    Get a list of GitHub tokens from the supplied file. Assumes one token each line, and ignores blank line.
    :param token_file: path to the token file
    :return: A list of GitHub tokens
    """
    if not os.path.exists(token_file):
        logging.error("Please put GitHub Tokens in {} for this script to work".format(token_file))
        return []
    with open(token_file, "r") as f:
        return list(x.strip() for x in f.readlines() if x.strip() != "")


def get_commit_link(repo_name: str, commit_sha: str) -> str:
    return "https://github.com/{}/commit/{}".format(repo_name, commit_sha)


def get_issue_link(repo_name: str, issue_number: int) -> str:
    return "https://github.com/{}/issues/{}".format(repo_name, issue_number)


def get_pr_link(repo_name: str, pr_number: int) -> str:
    return "https://github.com/{}/pull/{}".format(repo_name, pr_number)


def get_issues_in_text(repo_name: str, text: str) -> List[Tuple[str, int]]:
    """
    See https://docs.github.com/en/free-pro-team@latest/github/writing-on-github/
            autolinked-references-and-urls#issues-and-pull-requests
    :param repo_name: full repo name like "username/repository_name"
    :param text: the text to extract linked issues (e.g. commits)
    :return: Tuples of (repo_name, issue_number)
    """
    pattern = r"([\w\.\-_]+/[\w\.\-_]+)#(\d+)|#(\d+)|GH-(\d+)"
    result = []
    for match in re.finditer(pattern, text):
        # print(match.string)
        # print(text[match.start():match.end()])
        # print(match.groups())
        groups = match.groups()
        if groups[0] is not None and groups[1] is not None:
            result.append((groups[0], int(groups[1])))
        elif groups[2] is not None:
            result.append((repo_name, int(groups[2])))
        elif groups[3] is not None:
            result.append((repo_name, int(groups[3])))
    url_pattern = r"https://github\.com/([\w\.\-_]+/[\w\.\-_]+)/(issues|pull)/(\d+)"
    for match in re.finditer(url_pattern, text):
        result.append((match.groups()[0], int(match.groups()[2])))
    return result


def select_projects_from_libraries_io() -> pd.DataFrame:
    if os.path.exists("cache/projects.csv"):
        return pd.read_csv("cache/projects.csv")
    if not os.path.exists("cache"):
        os.mkdir("cache")

    db = pymongo.MongoClient(MONGO_URL).migration_helper

    projects = pd.DataFrame(list(db.lioRepository.find({
        "hostType": "GitHub",
        "fork": False,
        "language": "Java",
        "starsCount": {"$gt": 10},
    })))
    logging.debug(f"{len(projects)} non-fork GitHub Java projects with stars > 10")

    name_to_pom_count = Counter()
    name_to_pom_commits = defaultdict(set)
    for seq in db.wocDepSeq3.find():
        name = seq["repoName"].replace("_", "/")
        if len(seq["seq"]) >= 1:
            name_to_pom_count[name] += 1
        for item in seq["seq"]:
            name_to_pom_commits[name].add(item["commit"])

    projects = projects[projects["nameWithOwner"].isin(name_to_pom_count.keys())]
    projects["pomFilesCount"] = projects["nameWithOwner"].map(lambda n: name_to_pom_count[n])
    projects["pomFileModifyingCommitsCount"] = projects["nameWithOwner"].map(lambda n: len(name_to_pom_commits[n]))
    logging.debug(f"{len(projects)} non-fork GitHub Java projects with stars > 10 and one pom.xml file")

    projects["commitsCount"] = projects["_id"].map(lambda i: len(db.wocRepository.find_one({"_id": i})["commits"]))
    projects.to_csv("cache/projects.csv", index=False, encoding="utf-8")
    return projects


def select_libraries_from_libraries_io() -> pd.DataFrame:
    if os.path.exists("cache/libraries.csv"):
        return pd.read_csv("cache/libraries.csv")
    if not os.path.exists("cache"):
        os.mkdir("cache")

    db = pymongo.MongoClient(MONGO_URL).migration_helper
    libraries = pd.DataFrame(list(db.lioProject.find({
        "platform": "Maven",
        "dependentRepositoriesCount": {"$gt": 10}
    })))
    logging.debug(f"{len(libraries)} libraries with dependent repository count > 10")
    libraries.to_csv("cache/libraries.csv", index=False, encoding="utf-8")
    return libraries


def select_rules(valid_libs: Set[str]) -> pd.DataFrame:
    rules = pd.read_excel("data/rules.xlsx")
    return rules[rules["fromLib"].isin(valid_libs) & rules["toLib"].isin(valid_libs)]


def select_dependency_changes(project_name: str, valid_libs: Set[str] = None) -> pd.DataFrame:
    cache_path = f"cache/{project_name.replace('/', '_')}.csv"
    if os.path.exists(cache_path):
        results = pd.read_csv(cache_path).fillna("")
        if valid_libs is not None:
            valid_libs.add("")
            results = results[results["lib1"].isin(valid_libs) & results["lib2"].isin(valid_libs)]
        return results
    if not os.path.exists("cache"):
        os.mkdir("cache")

    db = pymongo.MongoClient(MONGO_URL).migration_helper
    results = []
    for dep_seq in db.wocDepSeq3.find({"repoName": project_name.replace("/", "_")}):
        for item in dep_seq["seq"]:
            for change in item["versionChanges"]:
                row = {
                    "project": project_name,
                    "commit": item["commit"],
                    "file": dep_seq["fileName"],
                    "type": "",
                    "lib1": "",
                    "lib2": "",
                    "ver1": "",
                    "ver2": "",
                }
                if change.startswith("+"):
                    row["type"] = "add"
                    row["lib2"], row["ver2"] = change[1:].split(" ")
                elif change.startswith("-"):
                    row["type"] = "rem"
                    row["lib1"], row["ver1"] = change[1:].split(" ")
                elif change.startswith(" "):
                    row["type"] = "verchg"
                    row["lib1"] = row["lib2"] = change[1:].split(" ")[0]
                    row["ver1"], row["ver2"] = change[1:].split(" ")[1].split("->")
                results.append(row)
    results = pd.DataFrame(results).fillna("")
    results.to_csv(cache_path, index=False)
    if valid_libs is not None:
        valid_libs.add("")
        results = results[results["lib1"].isin(valid_libs) & results["lib2"].isin(valid_libs)]
    return results


def plot_distribution(data: Iterable[any], file: str) -> None:
    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    res = get_issues_in_text("a/a", "cc#23 is abc GH-32 where abc/def#222 and a-c/D.f#333" +
                             " https://github.com/abc/def/issues/4444 sadwec " +
                             "https://github.com/abc./def-_/pull/5555")
    print(res)

    print(select_libraries_from_libraries_io())
    print(select_projects_from_libraries_io())
    print(select_rules(set(select_libraries_from_libraries_io()["name"])))
    print(select_dependency_changes("square/okhttp"))
    print(select_dependency_changes("square/okhttp", set(select_libraries_from_libraries_io()["name"])))
