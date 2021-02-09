from datetime import datetime
import pymongo
import pytz
import pandas as pd
from dateutil.parser import parse as dateParser
import datautil
import re
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Set
import csv
MONGO_URL = "mongodb://127.0.0.1:27017"
db = pymongo.MongoClient(MONGO_URL, connect=False).migration_helper
raw_db = pymongo.MongoClient(MONGO_URL).libraries


def get_migration_to_library(lib: str) -> pd.DataFrame:
    migration_commits = pd.read_csv('data/migration_changes.csv', dtype=object)
    lib_required = migration_commits['lib2'].map(lambda x: x == lib)
    migration_to_commits = migration_commits[lib_required]
    return migration_to_commits

def get_migration_to_library_before(lib: str, datetime: datetime) -> pd.DataFrame:
    migration_commits = pd.read_csv('data/migration_changes.csv', dtype=object)
    lib_required = migration_commits['lib2'].map(lambda x: x == lib)
    date_required = migration_commits['commit'].map(lambda x: get_commit_time(x) < datetime)
    migration_to_commits = migration_commits[lib_required & date_required]
    return migration_to_commits

def get_migration_from_library(lib: str) -> pd.DataFrame:
    migration_commits = pd.read_csv('data/migration_changes.csv', dtype=object)
    lib_required = migration_commits['lib1'].map(lambda x: x == lib)
    migration_from_commits = migration_commits[lib_required]
    return migration_from_commits

def get_migration_from_library_before(lib: str, datetime: datetime) -> pd.DataFrame:
    migration_commits = pd.read_csv('data/migration_changes.csv', dtype=object)
    lib_required = migration_commits['lib1'].map(lambda x: x == lib)
    date_required = migration_commits['commit'].map(lambda x: get_commit_time(x) < datetime)
    migration_from_commits = migration_commits[lib_required & date_required]
    return migration_from_commits


def get_commit_time(commit: str) -> datetime:
    c = db.wocCommit.find_one({"_id": commit})
    if c is not None:
        return c['timestamp'].replace(tzinfo=pytz.timezone('UTC'))

    else:
        return None


def get_library_nearest_published_time(lib: str, commit_time: datetime) -> datetime:
    library_versions = raw_db.versions.find({"Platform": "Maven", "Project Name": lib}, sort=[
                                            ("Published Timestamp", pymongo.DESCENDING)])
    for library_version in library_versions:
        published_time = dateParser(library_version['Published Timestamp'])
        if published_time < commit_time:
            return published_time


def get_library_first_published_time(lib: str) -> datetime:
    return dateParser(list(raw_db.versions.find({"Platform": "Maven", "Project Name": lib}, sort=[
        ("Published Timestamp", pymongo.ASCENDING)]))[0]["Published Timestamp"])


def get_project_before_config_direct_dependency(commit: str, config_filename: str) -> List:
    diffs = db.wocCommit.find_one({"_id": commit})['diffs']
    pom_blob = None
    for diff in diffs:
        if diff['filename'] == config_filename:
            pom_blob = diff['oldBlob']
    if not pom_blob:
        return None
    else:
        direct_dependencies = db.wocPomBlob.find_one({'_id': pom_blob})['dependencies']
        return direct_dependencies


def get_project_before_other_direct_dependency(project: str, commit: str, config_filename: str) -> pd.DataFrame:
    commits = db.wocRepository.find_one({"name": project.replace("/", "_")})['commits']
    migration_time = get_commit_time(commit)
    other_config_blobs = {}
    dependencies = []
    print(len(commits))
    i = 0
    for c in commits:
        if (i % 100 == 0):
            print(i)
        i += 1
        commit = db.wocCommit.find_one({"_id": c})
        if commit is None:
            continue
        commit_time = commit['timestamp'].replace(tzinfo=pytz.timezone('UTC'))
        if commit_time < migration_time:
            diffs = commit['diffs']
            for diff in diffs:
                if re.search(r'pom.xml', diff['filename']) is not None and config_filename != diff['filename']:
                    other_config_file = diff['filename']
                    if diff['filename'] not in other_config_blobs.keys():
                        other_config_blobs[other_config_file] = {"timestamp": commit_time, "blob": diff['newBlob']}
                    else:
                        if commit_time > other_config_blobs[other_config_file]['timestamp']:
                            other_config_blobs[other_config_file]['timestamp'] = commit_time
                            other_config_blobs[other_config_file]['blob'] = diff['newBlob']
    for value in other_config_blobs.values():
        if value['blob'] != "":
            dependencies.extend(db.wocPomBlob.find_one({'_id': value['blob']})['dependencies'])
    return pd.DataFrame(dependencies)


def get_library_direct_dependency(groupId: str, artifactId: str, version: str) -> List[dict]:
    dependencies = []
    projectName = groupId + ":" + artifactId
    if version != "" and '$' not in version and '[' not in version:
        results = list(db.lioProjectDependency.find(
            {"projectName": projectName, "versionNumber": {'$regex' :f"{version}.*"}}, sort=[
                ("version", pymongo.DESCENDING)]))        
    else:
        results = list(db.lioProjectDependency.find(
            {"projectName": projectName}, sort=[
                ("version", pymongo.DESCENDING)]))
    if results:
        versionNumber = results[0]['versionNumber']
        results = list(db.libraryVersionToDependency.find(
                {"projectName": projectName, "versionNumber": versionNumber}))
        for result in results:
            groupId, artifactId = result["projectName"].split(":")
            version = result["versionNumber"]
            dependencies.append({"groupId":groupId,"artifactId":artifactId, "version":version})
    return dependencies
    


def get_project_before_config_all_dependencies(commit: str, config_filename: str) -> pd.DataFrame:
    dependencies = []
    temp_dependencies = get_project_before_config_direct_dependency(commit, config_filename)
    while temp_dependencies:
        now_dependency = temp_dependencies.pop(0)
        if now_dependency in dependencies:
            continue
        else:
            dependencies.append(now_dependency)
        new_dependencies = get_library_direct_dependency(
            now_dependency['groupId'], now_dependency['artifactId'], now_dependency['version'])
        if new_dependencies:
            temp_dependencies.extend(new_dependencies)
            for d in new_dependencies:
                if d not in dependencies:
                    dependencies.append(d)
    return pd.DataFrame(dependencies)


def index_1(migration_change:np.ndarray, lib: str) -> int:
    change_time = get_commit_time(migration_change[2])
    library_nearest_time = get_library_nearest_published_time(lib, change_time)
    return (change_time - library_nearest_time).days


def index_2(migration_change: np.ndarray, lib: str) -> int:
    change_time = get_commit_time(migration_change[2])
    library_first_time = get_library_first_published_time(lib)
    return (change_time - library_first_time).days


def index_5(migration_change: np.ndarray, lib: str) -> int:
    groupId, artifactId = lib.split(':')
    all_dependencies = get_project_before_config_all_dependencies(
        migration_change[2], migration_change[3])
    if len(all_dependencies) == 0 or len(all_dependencies[(all_dependencies['groupId'] == groupId) & (all_dependencies['artifactId'] == artifactId)].index) == 0:
        return 0
    else:
        return 1


def index_6(migration_change: np.ndarray, lib: str) -> int:
    groupId, artifactId = lib.split(':')
    other_direct_dependencies = get_project_before_other_direct_dependency(migration_change[1],
        migration_change[2], migration_change[3])
    if len(other_direct_dependencies[(other_direct_dependencies['groupId'] == groupId) & (other_direct_dependencies['artifactId'] == artifactId)].index) == 0:
        return 0
    else:
        return 1


def get_library_retention_rate(migration_change:np.ndarray, lib: str) -> float:  # 7
    commit_time = get_commit_time(migration_change[2])
    remove = len(get_migration_from_library_before(lib, commit_time))
    add = len(get_migration_to_library_before(lib, commit_time))
    if add == 0:
        return float("-inf")
    return 1 - remove / add


def get_library_inflow_rate(migration_change:np.ndarray, lib: str) -> float:  # 8
    commit_time = get_commit_time(migration_change[2])
    add = len(list(db.wocConfirmedMigration.find(
        {"toLib": lib, "startCommitTime": {'$lt': commit_time}})))
    remove = len(list(db.wocConfirmedMigration.find(
        {"fromLib": lib, "startCommitTime": {'$lt': commit_time}})))
    if add == 0 and remove == 0:
        return 0
    return (add - remove) / (add + remove)


if __name__ == '__main__':
    # print(get_library_nearest_published_time("commons-codec:commons-codec", "e8aeaef43cbfb2b8a9b71c7b7f462c48b4adb9a6"))
    # print(get_library_first_published_time("commons-codec:commons-codec"))
    print(get_project_before_config_all_dependencies("7c65c5b167a85e28d21c58dc6c96c75bef04a444",
                                                     "pom.xml"))
    # print(get_project_before_other_direct_dependency("Snailclimb/JavaGuide", "e8aeaef43cbfb2b8a9b71c7b7f462c48b4adb9a6",
    #                                                  "docs/dataStructures-algorithms/source code/securityAlgorithm/pom.xml"))
    # print(get_library_direct_dependency("org.json", "json", ""))
    # print(get_library_retention_rate("junit:junit", "e8aeaef43cbfb2b8a9b71c7b7f462c48b4adb9a6"))
    # print(get_library_inflow_rate("junit:junit", "e8aeaef43cbfb2b8a9b71c7b7f462c48b4adb9a6"))

