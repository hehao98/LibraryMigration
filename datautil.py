import os
import pytz
import logging
import pymongo
import multiprocessing
import pandas as pd
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Set, Tuple


CACHE_DIR = "cache/"
MONGO_URL = "mongodb://127.0.0.1:27017"
if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)


def get_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (projects, libraries, migrations, rules, dep_changes).
    This function should be used get the required data for analysis,
        to avoid data scope inconsistencies in different analysis modules.
    """
    projects = select_projects_from_libraries_io()
    libraries = select_libraries()
    migrations = select_migrations()
    lib_names = set(libraries["name"])
    rules = select_rules(lib_names)
    dep_changes = select_dependency_changes_all(lib_names) 
    return projects, libraries, migrations, rules, dep_changes


def select_projects_from_libraries_io() -> pd.DataFrame:
    """Select a project dataframe as our research subject"""
    if os.path.exists(os.path.join(CACHE_DIR, "projects.csv")):
        return pd.read_csv(os.path.join(CACHE_DIR, "projects.csv"))

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
    projects.to_csv(os.path.join(CACHE_DIR, "projects.csv"), index=False)
    return projects


def select_libraries_from_libraries_io() -> pd.DataFrame:
    """Select a library dataframe as our research subject"""
    db = pymongo.MongoClient(MONGO_URL).migration_helper
    libraries = pd.DataFrame(list(db.lioProject.find({
        "platform": "Maven",
        "dependentRepositoriesCount": {"$gt": 10}
    })))
    logging.debug(
        f"{len(libraries)} libraries with dependent repository count > 10")
    return libraries


def select_libraries() -> pd.DataFrame:
    """Only keep libraries that has been added more than 10 times in our repository dataset"""
    if os.path.exists(os.path.join(CACHE_DIR, "libraries.csv")):
        return pd.read_csv(os.path.join(CACHE_DIR, "libraries.csv"))
    libraries = select_libraries_from_libraries_io()
    dep_changes = select_dependency_changes_all()
    added_projects = defaultdict(set)
    for idx, chg in dep_changes[dep_changes["type"] == "add"].iterrows():
        added_projects[chg["lib2"]].add(chg["project"])
    libraries["addedProjects"] = libraries["name"].map(lambda x: len(added_projects[x]))  
    libraries["versionsCount"] = libraries["name"].map(lambda x: len(select_library_versions(x)))
    libraries = libraries[libraries.addedProjects > 10].copy()
    libraries.to_csv(os.path.join(CACHE_DIR, "libraries.csv"), index=False)
    return libraries


def select_rules(valid_libs: Set[str]) -> pd.DataFrame:
    """Select a migration rule dataframe as our research subject"""
    rules = pd.read_excel("data/rules.xlsx", engine="openpyxl")
    return rules[rules["fromLib"].isin(
        valid_libs) & rules["toLib"].isin(valid_libs)]


def select_dependency_changes(
        project_name: str, valid_libs: Set[str] = None) -> pd.DataFrame or None:
    db = pymongo.MongoClient(MONGO_URL).migration_helper
    commits_non_merge = {c["_id"]: c["timestamp"]
            for c in select_commits_by_project(project_name) if len(c["parents"]) < 2}
    results = []
    for dep_seq in db.wocDepSeq3.find(
            {"repoName": project_name.replace("/", "_")}):
        for item in dep_seq["seq"]:
            if item["commit"] not in commits_non_merge:
                continue
            for change in item["versionChanges"]:
                row = {
                    "project": project_name,
                    "timestamp": commits_non_merge[item["commit"]],
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
    if valid_libs is not None:
        valid_libs.add("")
        results = results[results["lib1"].isin(
            valid_libs) & results["lib2"].isin(valid_libs)]
    return results


def select_dependency_changes_all(lib_names: set = None) -> pd.DataFrame:
    """If lib_names is not None, only keep dependency changes if both libraries are in the lib_names"""
    if os.path.exists(os.path.join(CACHE_DIR, "depchgs.csv")):
        dep_changes = pd.read_csv(os.path.join(CACHE_DIR, "depchgs.csv"), low_memory=False).fillna("")
    else:
        projects = select_projects_from_libraries_io()
        libraries = select_libraries_from_libraries_io()
        lib_names2 = set(libraries["name"])
        with multiprocessing.Pool(32) as pool:
            results = pool.starmap(
                select_dependency_changes,
                [(proj_name, lib_names2)
                for proj_name in projects["nameWithOwner"]]
            )
        dep_changes = pd.concat(filter(lambda x: x is not None, results))
        dep_changes.to_csv(os.path.join(CACHE_DIR, "depchgs.csv"), index=False)
    if lib_names is not None:
        lib_names = lib_names | set("")
        dep_changes = dep_changes[dep_changes.lib1.isin(lib_names) 
                                  | dep_changes.lib2.isin(lib_names)]
    return dep_changes


def select_commits_by_project(project_name: str) -> List[dict]:
    db = pymongo.MongoClient(MONGO_URL).migration_helper
    commit_shas = list(db.wocRepository.find_one(
        {"name": project_name.replace("/", "_")})["commits"])
    commits = list(db.wocCommit.find({"_id": {"$in": commit_shas}}))
    for c in commits:
        if type(c["timestamp"]) == datetime:
            c["timestamp"] = c["timestamp"].replace(tzinfo=pytz.timezone("UTC"))
    return commits


def select_library_versions(lib_name: str) -> List[dict]:
    db = pymongo.MongoClient(MONGO_URL).migration_helper
    group_id, artifact_id = lib_name.split(":")
    idx = db.libraryGroupArtifact.find_one(
        {"groupId": group_id, "artifactId": artifact_id})["_id"]
    return list(db.libraryVersion.find({"groupArtifactId": idx}))


def select_library_dependencies(lib_name: str, transitive=False) -> List[dict]:
    """NOTE: the version will only be kept as-is (i.e. no version resolution)"""
    db = pymongo.MongoClient(MONGO_URL).migration_helper
    deps = list(db.lioProjectDependency.find({"projectName": lib_name}))
    if not transitive:
        return deps
    libs = { x["dependencyName"]: x for x in deps }
    resolved_libs = set()
    while len(resolved_libs) != len(libs):
        for lib in set(libs.keys()) - resolved_libs:
            for dep in db.lioProjectDependency.find({"projectName": lib}):
                if dep["dependencyName"] not in libs:
                    libs[dep["dependencyName"]] = dep
            resolved_libs.add(libs)
    return list(libs.values())


def select_project_dependencies(proj_name: str) -> List[dict]:
    db = pymongo.MongoClient(MONGO_URL).migration_helper
    return list(db.lioRepositoryDependency.find({"repositoryNameWithOwner": proj_name}))
    

def select_migrations() -> pd.DataFrame:
    migrations = pd.read_excel("data/migrations.xlsx", engine="openpyxl")
    lib_names = set(select_libraries()["name"])
    return migrations[migrations["fromLib"].isin(
        lib_names) & migrations["toLib"].isin(lib_names)].copy()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print(select_libraries_from_libraries_io())
    print(select_projects_from_libraries_io())
    print(select_rules(set(select_libraries_from_libraries_io()["name"])))

    print(select_commits_by_project("square/okhttp")[0:10])

    print(select_dependency_changes("square/okhttp"))
    print(select_dependency_changes("square/okhttp",
                                    set(select_libraries_from_libraries_io()["name"])))
    print(select_dependency_changes("bumptech/glide"))
    print(select_dependency_changes("dropwizard/dropwizard"))
    
    print(select_library_dependencies("org.jboss.resteasy:resteasy-jackson-provider"))

    print(len(select_dependency_changes_all()))
    print(get_data())
