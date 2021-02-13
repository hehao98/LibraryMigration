import os
import re
import pymongo
import pytz
import logging
import datautil
import numpy as np
import pandas as pd
import multiprocessing as mp
from datetime import datetime
from dateutil.parser import parse as dateParser
from collections import defaultdict
from typing import List
from lxml import etree


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


MONGO_URL = "mongodb://127.0.0.1:27017"
db = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=200).migration_helper
dblio = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=200).libraries
lib2versions = defaultdict(list)
lib2vulnerabilities = defaultdict(list)
lib2adoptions = defaultdict(pd.Series)
lib2removals = defaultdict(pd.Series)
lib2migrations = defaultdict(set)
lib2license = defaultdict(str)


def get_library_nearest_published_time(lib: str, timestamp: datetime) -> datetime:
    global lib2versions
    for library_version in reversed(lib2versions[lib]):
        published_time = library_version["Published Timestamp"]
        if published_time < timestamp:
            return published_time
    return timestamp


def get_library_first_published_time(lib: str) -> datetime:
    global lib2versions
    return lib2versions[lib][0]["Published Timestamp"]


def get_library_retention(lib, timestamp) -> float:
    global lib2adoptions
    global lib2removals
    add = len(lib2adoptions[lib].truncate(after=timestamp))
    rem = len(lib2removals[lib].truncate(after=timestamp))
    return max(0, 1 - rem / max(1, add))


def get_library_flow(lib, timestamp) -> float:
    global lib2migrations
    ind = len([x for x in lib2migrations[lib] if x[1] == lib and x[3] < timestamp])
    outd = len([x for x in lib2migrations[lib] if x[0] == lib and x[3] < timestamp])
    return (ind - outd) / max(1, outd + ind)


def get_metrics_per_project(proj: str, proj_changes: pd.DataFrame) -> pd.DataFrame:
    global lib2vulnerabilities
    global lib2license

    proj_changes = proj_changes.copy()

    metrics = defaultdict(list)
    for change in proj_changes.itertuples():
        if change.type == "add":
            lib = change.lib2
            metrics["response"].append(1)
        else:
            lib = change.lib1
            metrics["response"].append(0)
        metrics["last_release_interval"].append(
            (change.timestamp - get_library_nearest_published_time(lib, change.timestamp)).days)
        metrics["first_release_interval"].append(
            (change.timestamp - get_library_first_published_time(lib)).days)
        metrics["vulnerabilities"].append(
            len([x for x in lib2vulnerabilities[lib] if x < change.timestamp]))
        metrics["license"].append(lib2license[lib])
        metrics["retention"].append(get_library_retention(lib, change.timestamp))
        metrics["flow"].append(get_library_flow(lib, change.timestamp))
    
    for metric, values in metrics.items():
        proj_changes[metric] = values
    return proj_changes


def init_cache(libraries: pd.DataFrame, dep_changes: pd.DataFrame, migrations: pd.DataFrame):
    global lib2versions
    global lib2vulnerabilities
    global lib2adoptions
    global lib2removals
    global lib2migrations
    global lib2license

    logging.info("Caching library versions...")
    for lib in libraries.name:
        lib2versions[lib] = list(dblio.versions.find({"Platform": "Maven", "Project Name": lib}))
        for x in lib2versions[lib]:
            x["Published Timestamp"] = dateParser(x["Published Timestamp"]).replace(tzinfo=pytz.timezone("UTC"))
        lib2versions[lib] = sorted(lib2versions[lib], key=lambda x: x["Published Timestamp"])
        lib2license[lib] = dblio.projects.find_one({"Platform": "Maven", "Name": lib})["Licenses"]

    logging.info("Caching CVEs...")
    cve2time = defaultdict(list)
    tree = etree.parse("data/cve.xml")
    root = tree.getroot()
    for item in root.findall("item", root.nsmap):
        cve = item.get("name")
        date = cve.split("-")[1]
        if len(item.findall("phase", root.nsmap)) > 0:
            date = item.findall("phase", root.nsmap)[0].get("date")
        t = dateParser(date).replace(tzinfo=pytz.timezone("UTC"))
        cve2time[cve] = t
    vuln = pd.read_excel("data/vulnerabilities_github.xlsx", parse_dates=["publishedAt"])
    for lib, cve, published_at in zip(vuln.package, vuln.CVE, vuln.publishedAt):
        if cve in cve2time:
            lib2vulnerabilities[lib].append(cve2time[cve])
        else:
            lib2vulnerabilities[lib].append(published_at)

    logging.info("Caching for retention rate...")
    for lib, df in dep_changes[dep_changes.type == "add"].sort_values(by="timestamp").groupby("lib2"):
        lib2adoptions[lib] = pd.Series(list(df.type), index=pd.DatetimeIndex(list(df.timestamp)))
    for lib, df in dep_changes[dep_changes.type == "rem"].sort_values(by="timestamp").groupby("lib1"):
        lib2removals[lib] = pd.Series(list(df.type), index=pd.DatetimeIndex(list(df.timestamp)))

    logging.info("Caching for migration...")
    for mig in migrations.itertuples():
        item = (mig.fromLib, mig.toLib, mig.repoName, mig.startCommitTime)
        lib2migrations[mig.fromLib].add(item)
        lib2migrations[mig.toLib].add(item)


def run():
    projects, libraries, migrations, rules, dep_changes = datautil.get_data()
    dep_changes = dep_changes[(dep_changes.type == "add") | (dep_changes.type == "rem")]
    dep_changes.timestamp = pd.to_datetime(dep_changes.timestamp)
    migrations.startCommitTime = pd.to_datetime(migrations.startCommitTime, utc=True)

    init_cache(libraries, dep_changes, migrations)
    
    logging.info("Computing metrics...")
    with mp.Pool(mp.cpu_count() // 2) as pool:
        dep_changes = pd.concat(pool.starmap(get_metrics_per_project, list(dep_changes.groupby(by="project"))))

    logging.info("Exporting data...")
    dep_changes.to_csv(os.path.join(datautil.CACHE_DIR, "model_data.csv"), index=False)
    
