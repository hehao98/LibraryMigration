import os
import re
import pymongo
import pytz
import logging
import functools
import datautil
import pandas as pd
import multiprocessing as mp
from copy import deepcopy
from datetime import datetime
from dateutil.parser import parse as dateParser
from collections import defaultdict
from typing import Tuple
from lxml import etree


MONGO_URL = "mongodb://127.0.0.1:27017"
lib2versions = defaultdict(list)
lib2vulnerabilities = defaultdict(list)
lib2adoptions = defaultdict(pd.Series)
lib2removals = defaultdict(pd.Series)
lib2migrations = defaultdict(set)
lib2license = defaultdict(str)
lib2deps = defaultdict(lambda : defaultdict(dict))      # group_id:artifact_id -> version -> {groupId:artifactId: version}
lib2transdeps = defaultdict(lambda : defaultdict(dict)) # group_id:artifact_id -> version -> {groupId:artifactId: version}


def lru_cache(maxsize=128, typed=False, copy=False):
    """An LRU cache that deep copies returned value"""
    if not copy:
        return functools.lru_cache(maxsize, typed)
    def decorator(f):
        cached_func = functools.lru_cache(maxsize, typed)(f)
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return deepcopy(cached_func(*args, **kwargs))
        return wrapper
    return decorator


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


def get_library_last_published_time(lib: str) -> datetime:
    global lib2versions
    return lib2versions[lib][-1]["Published Timestamp"]


def get_library_release_freq(lib: str, timestamp: datetime) -> int:
    global lib2versions
    t1 = get_library_first_published_time(lib)
    t2 = get_library_nearest_published_time(lib, timestamp)
    cnt = len([v for v in lib2versions[lib] if t1 <= v["Published Timestamp"] <= t2])
    return (t2 - t1).days // max(1, cnt)


def get_library_retention(lib: str, timestamp) -> float:
    global lib2adoptions
    global lib2removals
    add = len(lib2adoptions[lib].truncate(after=timestamp))
    rem = len(lib2removals[lib].truncate(after=timestamp))
    return max(0, 1 - rem / max(1, add))


def get_library_flow(lib: str, timestamp) -> float:
    global lib2migrations
    ind = len([x for x in lib2migrations[lib] if x[1] == lib and x[3] < timestamp])
    outd = len([x for x in lib2migrations[lib] if x[0] == lib and x[3] < timestamp])
    if ind == 0 and outd == 0:
        return 0
    return (ind - outd) / (outd + ind)


def parse_version(version: str) -> str:
    # ref: https://stackoverflow.com/questions/6618868
    if match := re.search("(\d+(?:\.\d+)+[-.]?[a-zA-Z\d]*)", version):
        return match.group(1)
    else:
        return ""


@lru_cache(maxsize=32768, copy=True)
def get_direct_dependencies(lib: str, version: str) -> dict:
    global lib2versions

    db = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=200).migration_helper
    group_id, artifact_id = lib.split(":")[0], lib.split(":")[1]
    res = []

    # skip 1-4 if version is empty
    if version != "":
        # 1. exact matching
        res = list(db.libraryVersionToDependency.find(
            {"groupId": group_id, "artifactId": artifact_id, "version": version},
            sort=[("version", pymongo.DESCENDING)]))
        # 2. version*
        if not res:
            version_ = version
            res = list(db.libraryVersionToDependency.find(
                {"groupId": group_id, "artifactId": artifact_id, "version": {'$regex' :f"^{version_}"}},
                sort=[("version", pymongo.DESCENDING)]))
        # 3. remove dash
        if not res and '-' in version:
            version_= version.split('-')[0]
            res = list(db.libraryVersionToDependency.find(
                {"groupId": group_id, "artifactId": artifact_id, "version": {'$regex' :f"^{version_}"}},
                sort=[("version", pymongo.DESCENDING)]))
        # 4. remove last dot
        if not res:
            version_= '.'.join(version.split('.')[:-1])
            # version_ may be an empty string?
            if version_:
                res = list(db.libraryVersionToDependency.find(
                    {"groupId": group_id, "artifactId": artifact_id, "version": {'$regex' :f"^{version_}"}},
                    sort=[("version", pymongo.DESCENDING)]))
    # 5. find all
    if not res:
        res = list(db.libraryVersionToDependency.find({"groupId": group_id, "artifactId": artifact_id},
            sort=[("version", pymongo.DESCENDING)]))
    # 6. report error
    if not res:
        logging.error("%s %s", lib, version)
        return {}
    
    res = res[0]
    for i, dep in enumerate(res["dependencies"]):
        for key in ["groupId", "artifactId", "version"]:
            res["dependencies"][i][key] = dep[key].replace("${project.groupId}", group_id)
            res["dependencies"][i][key] = dep[key].replace("${project.artifactId}", artifact_id)
            res["dependencies"][i][key] = dep[key].replace("${project.version}", res["version"])
        res["dependencies"][i]["version"] = parse_version(dep["version"])
    return {x["groupId"] + ":" + x["artifactId"]: x["version"] for x in res["dependencies"]
        if x["groupId"] + ":" + x["artifactId"] in lib2versions}


def resolve_version(lib: str, ver: str) -> str:
    global lib2versions
    vernums = [str(x["Number"]) for x in lib2versions[lib]]
    if ver in vernums:
        return ver
    perfixes = [v for v in vernums if v.startswith(ver)]
    if len(perfixes) > 0:
        return perfixes[-1]
    if ver.split('-')[0] in vernums:
        return ver.split('-')[0]
    if parse_version(ver) in vernums:
        return parse_version(ver)
    if '.'.join(ver.split('.')[:-1]) in vernums:
        return '.'.join(ver.split('.')[:-1])
    return vernums[-1]


def get_transitive_dependencies(lib: str, ver: str) -> dict:
    deps = get_direct_dependencies(lib, ver)
    while True:
        new_deps = dict()
        for lib2, ver2 in deps.items():
            for lib3, ver3 in get_direct_dependencies(lib2, ver2).items():
                if lib3 not in deps:
                    new_deps[lib3] = ver3
        if len(new_deps) == 0:
            break
        for dep2, ver2 in new_deps.items():
            deps[dep2] = ver2
    return deps


def get_dependencies(lib: str) -> Tuple[dict, dict]:
    db = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=200).migration_helper
    ver2deps = defaultdict(dict) # version string (this lib) -> "groupId:artifactId" -> version string (that lib)
    ver2transdeps = defaultdict(dict) # version string (this lib) -> "groupId:artifactId" -> version string (that lib)

    group_id, artifact_id = lib.split(":")[0], lib.split(":")[1]
    for item in db.libraryVersionToDependency.find({"groupId": group_id, "artifactId": artifact_id}):
        ver2deps[item["version"]] = get_direct_dependencies(lib, item["version"])

    for ver in ver2deps:
        ver2transdeps[ver] = deepcopy(ver2deps[ver])
        for lib2, ver2 in ver2deps[ver].items():
            for lib3, ver3 in get_transitive_dependencies(lib2, ver2).items():
                if lib3 not in ver2transdeps[ver]:
                    ver2transdeps[ver][lib3] = ver3

    logging.info("Finished getting dependencies for library %s", lib)
    return lib, ver2deps, ver2transdeps


def get_metrics_per_project(proj: str, proj_changes: pd.DataFrame) -> pd.DataFrame:
    global lib2vulnerabilities
    global lib2license
    global lib2transdeps

    proj_changes = proj_changes.sort_values(by="timestamp").copy()
    
    metrics = []
    file2deps = defaultdict(dict) # pom.xml path -> list of dependencies
    for commit, changes in proj_changes.groupby(by="commit"):
        f2removed_libs = defaultdict(set)
        for change in changes[changes.type == "rem"].itertuples():
            f2removed_libs[change.file].add(change.lib2)
        for change in changes.itertuples():
            metric = change._asdict()
            if "Index" in metric:
                del metric["Index"]

            if change.type == "add":
                lib = change.lib2
                metric["response"] = 1
            elif change.type == "rem":
                lib = change.lib1
                metric["response"] = 0
            else:
                continue
            metric["last_release_interval"] = (change.timestamp 
                                               - get_library_last_published_time(lib)).days
            metric["first_release_interval"] = (change.timestamp - get_library_first_published_time(lib)).days
            metric["nearest_release_inteveral"] = (change.timestamp 
                                               - get_library_nearest_published_time(lib, change.timestamp)).days
            metric["release_freq"] = get_library_release_freq(lib, change.timestamp)
            metric["vulnerabilities"] = len([x for x in lib2vulnerabilities[lib] if x < change.timestamp])
            metric["license"] = lib2license[lib]
            metric["retention"] = get_library_retention(lib, change.timestamp)
            metric["flow"] = get_library_flow(lib, change.timestamp)
            metric["in_other_file"] = any(lib in file2deps[f] for f in file2deps if f != change.file and lib not in f2removed_libs[f])
            metric["in_trans_dep"] = any(lib in lib2transdeps[lib2][ver2] and lib not in file2deps[change.file]
                                        for lib2, ver2 in file2deps[change.file].items())

            metrics.append(metric)

        for change in changes.itertuples():
            if change.type == "add":
                file2deps[change.file][change.lib2] = change.ver2
            elif change.type == "rem":
                if change.lib1 in file2deps[change.file]:
                    del file2deps[change.file][change.lib1]
            else: # version change
                file2deps[change.file][change.lib1] = change.ver2

    logging.info("Finished getting metrics for project %s", proj)
    return pd.DataFrame(metrics)


def init_cache(libraries: pd.DataFrame, dep_changes: pd.DataFrame, migrations: pd.DataFrame):
    global lib2versions
    global lib2vulnerabilities
    global lib2adoptions
    global lib2removals
    global lib2migrations
    global lib2license
    global lib2deps
    global lib2transdeps

    dblio = pymongo.MongoClient(MONGO_URL, connect=False, maxPoolSize=200).libraries

    logging.info("Caching library versions and license...")
    for lib in libraries.name:
        lib2versions[lib] = list(dblio.versions.find({"Platform": "Maven", "Project Name": lib}))
        for x in lib2versions[lib]:
            x["Published Timestamp"] = dateParser(x["Published Timestamp"]).replace(tzinfo=pytz.timezone("UTC"))
        lib2versions[lib] = sorted(lib2versions[lib], key=lambda x: x["Published Timestamp"])
        lib2license[lib] = dblio.projects.find_one({"Platform": "Maven", "Name": lib})["Licenses"]

    logging.info("Caching library dependencies for %s versions...", sum(len(lib2versions[x]) for x in lib2versions))
    with mp.Pool(mp.cpu_count() // 2) as pool:
        for lib, ver2deps, ver2transdeps in pool.map(get_dependencies, list(libraries.name)):
            lib2deps[lib] = ver2deps
            lib2transdeps[lib] = ver2transdeps

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
    dep_changes.timestamp = pd.to_datetime(dep_changes.timestamp)
    migrations.startCommitTime = pd.to_datetime(migrations.startCommitTime, utc=True)

    init_cache(libraries, dep_changes, migrations)
    
    logging.info("Computing metrics...")
    with mp.Pool(mp.cpu_count() // 2) as pool:
        dep_changes = pd.concat(pool.starmap(get_metrics_per_project, list(dep_changes.groupby(by="project"))))

    logging.info("Exporting data...")
    dep_changes.to_csv(os.path.join(datautil.CACHE_DIR, "model_data.csv"), index=False)
