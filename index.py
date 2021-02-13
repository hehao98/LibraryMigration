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
import multiprocessing
from itertools import repeat
from pathos.pools import ProcessPool
import time
from tqdm import tqdm
MONGO_URL = "mongodb://127.0.0.1:27017"
db = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=200).migration_helper
raw_db = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=200).libraries
migration_commits = pd.read_csv('data/migration_changes_with_time.csv', dtype=object)
migration_commits_values = migration_commits.values

def get_migration_to_library(lib: str) -> pd.DataFrame:
    lib_required = migration_commits['lib2'].map(lambda x: x == lib)
    type_required = migration_commits['type'].map(lambda x: x == 'add')
    migration_to_commits = migration_commits[lib_required & type_required]
    return migration_to_commits

def get_migration_to_library_before(lib: str, datetime: datetime) -> pd.DataFrame:
    datetime = str(datetime)
    migration_to_commits_before = migration_commits_values[(migration_commits_values[:, -1] < str(datetime)) & (migration_commits_values[:, 5] == lib) &( migration_commits_values[:, 3] == 'add')]
    return len(migration_to_commits_before)

def get_migration_to()->np.ndarray:
    type_required = migration_commits['type'].map(lambda x: x == 'add')
    migration_to_commits = migration_commits[type_required]
    return migration_to_commits

def get_migration_from()->np.ndarray:
    type_required = migration_commits['type'].map(lambda x: x == 'rem')
    migration_from_commits = migration_commits[type_required]
    return migration_from_commits

def get_migration_from_library(lib: str) -> pd.DataFrame:
    type_required = migration_commits['type'].map(lambda x: x == 'rem')
    lib_required = migration_commits['lib1'].map(lambda x: x == lib)
    migration_from_commits = migration_commits[lib_required & type_required]
    return migration_from_commits

def get_migration_from_library_before(lib: str, datetime: datetime) -> pd.DataFrame:
    datetime = str(datetime)
    migration_from_commits_before = migration_commits_values[(migration_commits_values[:, -1] < str(datetime)) & (migration_commits_values[:, 4] == lib) &( migration_commits_values[:, 3] == 'rem')]
    return len(migration_from_commits_before)


def get_commit_time(commit: str) -> datetime:
    c = db.wocCommit.find_one({"_id": commit})
    if c is not None:
        return c['timestamp'].replace(tzinfo=pytz.timezone('UTC'))

    else:
        return None


def get_library_nearest_published_time(lib: str, commit_time: datetime) -> datetime:
    raw_dbt = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=None).libraries
    library_versions = list(raw_dbt.versions.find({"Platform": "Maven", "Project Name": lib}, sort=[
                                            ("Published Timestamp", pymongo.DESCENDING)]))
    for library_version in library_versions:
        published_time = dateParser(library_version['Published Timestamp'])
        if published_time < commit_time:
            return published_time
    return None


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
    change_time = dateParser(migration_change[8])
    library_nearest_time = get_library_nearest_published_time(lib, change_time)
    if library_nearest_time:
        return (change_time - library_nearest_time).days
    else:
        return np.nan


def index_2(migration_change: np.ndarray, lib: str) -> int:
    change_time = dateParser(migration_change[8])
    library_first_time = get_library_first_published_time(lib)
    return (change_time - library_first_time).days

def index_1_all(migration_change:np.ndarray) -> int:
    if migration_change[3] == 'add':
        lib = migration_change[5]
    elif migration_change[3] == 'rem':
        lib = migration_change[4]
    else:
        return np.nan
    change_time = dateParser(migration_change[8])
    library_nearest_time = get_library_nearest_published_time(lib, change_time)
    if library_nearest_time:
        return (change_time - library_nearest_time).days
    else:
        return np.nan


def index_2_all(migration_change: np.ndarray) -> int:
    if migration_change[3] == 'add':
        lib = migration_change[5]
    elif migration_change[3] == 'rem':
        lib = migration_change[4]
    else:
        return np.nan
    change_time = dateParser(migration_change[8])
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
    # commit_time = get_commit_time(migration_change[2])
    commit_time = migration_change[8]
    remove = get_migration_from_library_before(lib, commit_time)
    add = get_migration_to_library_before(lib, commit_time)
#     if add == 0:
#         return float("-inf")
#     return 1 - remove / add
    if add == 0 and remove == 0:
        return 0
    return add / (add + remove)


def get_library_inflow_rate(migration_change:np.ndarray, lib: str) -> float:  # 8
    dbt = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=200).migration_helper
    commit_time = dateParser(migration_change[8])
    add = len(list(dbt.wocConfirmedMigration.find(
        {"toLib": lib, "startCommitTime": {'$lt': commit_time}})))
    remove = len(list(dbt.wocConfirmedMigration.find(
        {"fromLib": lib, "startCommitTime": {'$lt': commit_time}})))
    if add == 0 and remove == 0:
        return 0
    return (add - remove) / (add + remove)

def get_library_retention_rate_all(migration_change:np.ndarray) -> float:  # 7
    if migration_change[3] == 'add':
        lib = migration_change[5]
    elif migration_change[3] == 'rem':
        lib = migration_change[4]
    else:
        return np.nan
    commit_time = migration_change[8]
    remove = get_migration_from_library_before(lib, commit_time)
    add = get_migration_to_library_before(lib, commit_time)
#     if add == 0:
#         return float("-inf")
#     return 1 - remove / add
    if add == 0 and remove == 0:
        return 0
    return add / (add + remove)


def get_library_inflow_rate_all(migration_change:np.ndarray) -> float:  # 8
    dbt = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=None).migration_helper
    if migration_change[3] == 'add':
        lib = migration_change[5]
    elif migration_change[3] == 'rem':
        lib = migration_change[4]
    else:
        return np.nan
    commit_time = dateParser(migration_change[8])
    add = len(list(dbt.wocConfirmedMigration.find(
        {"toLib": lib, "startCommitTime": {'$lt': commit_time}})))
    remove = len(list(dbt.wocConfirmedMigration.find(
        {"fromLib": lib, "startCommitTime": {'$lt': commit_time}})))
    if add == 0 and remove == 0:
        return 0
    return (add - remove) / (add + remove)

def parallel(func, *args, show=False):
    pool = ProcessPool(48)
    try:
        if show:
            start = time.time()
            # imap方法
            with tqdm(total=len(args[0]), desc="计算进度") as t:  # 进度条设置
                r = []
                for i in pool.imap(func, *args):
                    r.append(i)
                    t.set_postfix({'并行函数': func.__name__, "计算花销": "%ds" % (time.time() - start)})
                    t.update()
            return r
        else:
            r = pool.map(func, *args)
            return r
    except Exception as e:
        print(e)
    finally:
        # 关闭池
        pool.close()  # close the pool to any new jobs
        pool.join()  # cleanup the closed worker processes
        pool.clear()  # Remove server with matching state
        
if __name__ == '__main__':
    print('start')
    index = [get_library_retention_rate_all, get_library_inflow_rate_all]
    for f in index:
        name = f.__name__[:-4]
        print(f.__name__[:-4])
        index = np.array([])
        start = time.time()
        data = migration_commits_values
        index = np.append(index, parallel(f, data))
        dataf = pd.DataFrame(data)
        print(f'timecost: {time.time() - start}')
        dataf[name] = index
        print(dataf.head(5))
        dataf.to_csv(f'data/migration_changes_with_{name}.csv', index=False)
