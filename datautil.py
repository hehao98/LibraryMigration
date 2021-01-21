import os
import logging
import pymongo
import multiprocessing
import pandas as pd
from collections import Counter, defaultdict
from typing import List, Set


MONGO_URL = "mongodb://127.0.0.1:27017"
CACHE_DIR = "../cache/"
if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)


def select_projects_from_libraries_io() -> pd.DataFrame:
    project_csv_path = os.path.join(CACHE_DIR, "projects.csv")
    if os.path.exists(project_csv_path):
        return pd.read_csv(project_csv_path)

    db = pymongo.MongoClient(MONGO_URL).migration_helper

    projects = pd.DataFrame(list(db.lioRepository.find({
        "hostType": "GitHub",
        "fork": False,
        "language": "Java",
        "starsCount": {"$gt": 10},
    })))
    logging.debug(
        f"{len(projects)} non-fork GitHub Java projects with stars > 10")

    name_to_pom_count = Counter()
    name_to_pom_commits = defaultdict(set)
    for seq in db.wocDepSeq3.find():
        name = seq["repoName"].replace("_", "/")
        if len(seq["seq"]) >= 1:
            name_to_pom_count[name] += 1
        for item in seq["seq"]:
            name_to_pom_commits[name].add(item["commit"])

    projects = projects[projects["nameWithOwner"].isin(
        name_to_pom_count.keys())]
    projects["pomFilesCount"] = projects["nameWithOwner"].map(
        lambda n: name_to_pom_count[n])
    projects["pomFileModifyingCommitsCount"] = projects["nameWithOwner"].map(
        lambda n: len(name_to_pom_commits[n]))
    logging.debug(
        f"{len(projects)} non-fork GitHub Java projects with stars > 10 and one pom.xml file")

    projects["commitsCount"] = projects["_id"].map(
        lambda i: len(db.wocRepository.find_one({"_id": i})["commits"]))
    projects.to_csv(project_csv_path, index=False, encoding="utf-8")
    return projects


def select_libraries_from_libraries_io() -> pd.DataFrame:
    library_csv_path = os.path.join(CACHE_DIR, "libraries.csv")
    if os.path.exists(library_csv_path):
        return pd.read_csv(library_csv_path)

    db = pymongo.MongoClient(MONGO_URL).migration_helper
    libraries = pd.DataFrame(list(db.lioProject.find({
        "platform": "Maven",
        "dependentRepositoriesCount": {"$gt": 10}
    })))
    logging.debug(
        f"{len(libraries)} libraries with dependent repository count > 10")
    libraries.to_csv(library_csv_path, index=False, encoding="utf-8")
    return libraries


def select_rules(valid_libs: Set[str]) -> pd.DataFrame:
    rules = pd.read_excel("data/rules.xlsx", engine="openpyxl")
    return rules[rules["fromLib"].isin(
        valid_libs) & rules["toLib"].isin(valid_libs)]


def select_dependency_changes(
        project_name: str, valid_libs: Set[str] = None) -> pd.DataFrame or None:
    cache_path = os.path.join(
        CACHE_DIR, project_name.replace(
            '/', '_') + ".csv")
    if os.path.exists(cache_path):
        results = pd.read_csv(cache_path).fillna("")
        if valid_libs is not None:
            valid_libs.add("")
            results = results[results["lib1"].isin(
                valid_libs) & results["lib2"].isin(valid_libs)]
        return results

    db = pymongo.MongoClient(MONGO_URL).migration_helper
    commits_non_merge = set(
        c["_id"] for c in select_commits_by_project(project_name) if len(
            c["parents"]) < 2)
    results = []
    for dep_seq in db.wocDepSeq3.find(
            {"repoName": project_name.replace("/", "_")}):
        for item in dep_seq["seq"]:
            if item["commit"] not in commits_non_merge:
                continue
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
                try:
                    if change.startswith("+"):
                        row["type"] = "add"
                        row["lib2"], row["ver2"] = change[1:].split(" ")[0:2]
                    elif change.startswith("-"):
                        row["type"] = "rem"
                        row["lib1"], row["ver1"] = change[1:].split(" ")[0:2]
                    elif change.startswith(" "):
                        row["type"] = "verchg"
                        row["lib1"] = row["lib2"] = change[1:].split(" ")[0]
                        row["ver1"], row["ver2"] = "".join(
                            change[1:].split(" ")[1:]).split("->")
                    results.append(row)
                except ValueError as e:
                    logging.error(f"Error while parsing \"{change}\": {e}")
    if len(results) == 0:
        return None
    results = pd.DataFrame(results).fillna("")
    results.to_csv(cache_path, index=False)
    if valid_libs is not None:
        valid_libs.add("")
        results = results[results["lib1"].isin(
            valid_libs) & results["lib2"].isin(valid_libs)]
    return results


def select_dependency_changes_all() -> pd.DataFrame:
    projects = select_projects_from_libraries_io()
    libraries = select_libraries_from_libraries_io()
    lib_names = set(libraries["name"])
    with multiprocessing.Pool(32) as pool:
        results = pool.starmap(
            select_dependency_changes,
            [(proj_name, lib_names) for proj_name in projects["nameWithOwner"]]
        )
    dep_changes = pd.concat(filter(lambda x: x is not None, results))
    return dep_changes


def select_commits_by_project(project_name: str) -> List[dict]:
    db = pymongo.MongoClient(MONGO_URL).migration_helper
    commit_shas = list(db.wocRepository.find_one(
        {"name": project_name.replace("/", "_")})["commits"])
    return list(db.wocCommit.find({"_id": {"$in": commit_shas}}))


def select_library_versions(lib_name: str) -> List[dict]:
    db = pymongo.MongoClient(MONGO_URL).migration_helper
    group_id, artifact_id = lib_name.split(":")
    idx = db.libraryGroupArtifact.find_one(
        {"groupId": group_id, "artifactId": artifact_id})["_id"]
    return list(db.libraryVersion.find({"groupArtifactId": idx}))


def select_migrations() -> pd.DataFrame:
    migrations = pd.read_excel("data/migrations.xlsx", engine="openpyxl")
    lib_names = set(select_libraries_from_libraries_io()["name"])
    return migrations[migrations["fromLib"].isin(
        lib_names) & migrations["toLib"].isin(lib_names)].copy()


if __name__ == "__main__":
    print(select_libraries_from_libraries_io())
    print(select_projects_from_libraries_io())
    print(select_rules(set(select_libraries_from_libraries_io()["name"])))
    print(select_dependency_changes("square/okhttp"))
    print(select_dependency_changes("square/okhttp",
                                    set(select_libraries_from_libraries_io()["name"])))
    print(select_dependency_changes("bumptech/glide"))
    print(select_dependency_changes("dropwizard/dropwizard"))
