import pymongo
from dateutil.parser import parse as dateParser
from dateutil import rrule
MONGO_URL = "mongodb://127.0.0.1:27017"
db = pymongo.MongoClient(MONGO_URL).migration_helper


def getProjectUsing(lib: str):
    proD = db['lioProjectDependency']
    myquery = {"dependencyName": {'$regex': 'org.json:json'}}
    mydoc = proD.find(myquery)
    projectsUsing = []
    for i in mydoc:
        id = i['projectId']
        if id not in projectsUsing:
            projectsUsing.append(id)
    return projectsUsing


def getMigrationAwayCommits(from_lib: str):
    commits = []
    results = db.wocConfirmedMigration.find(
        {"fromLib": from_lib})
    for result in results:
        commit = result['startCommit']
        if not commits or commits[-1] != commit:
            commits.append(commit)
    return commits


def getMigrationToCommits(to_lib: str):
    commits = []
    results = db.wocConfirmedMigration.find(
        {"toLib": to_lib})
    for result in results:
        commit = result['startCommit']
        if not commits or commits[-1] != commit:
            commits.append(commit)
    return commits


def getMigrationTime(commit: str):
    return db.wocConfirmedMigration.find_one({"startCommit": commit})['startCommitTime']


def getLibraryPublishTime(lib: str):
    repositoryId = db.lioProject.find_one({"name": lib})['repositoryId']
    return dateParser(db.lioRepository.find_one({"_id": repositoryId})['createdTimestamp'])


def getDirectDependencies(groupId: str, artifactId: str, version: str):
    if version != "" and '$' not in version:
        return db.libraryVersionToDependency.find_one(
            {"groupId": groupId, "artifactId": artifactId, "version": version})['dependencies']
    else:
        return db.libraryVersionToDependency.find_one(
            {"groupId": groupId, "artifactId": artifactId})['dependencies']


def getAllDependencies(groupId: str, artifactId: str, version: str):
    dependencies = getDirectDependencies(groupId, artifactId, version)
    tempDependencies = getDirectDependencies(groupId, artifactId, version)
    while tempDependencies:
        nowDependency = tempDependencies.pop(0)
        newDependencies = getDirectDependencies(
            nowDependency['groupId'], nowDependency['artifactId'], nowDependency['version'])
        tempDependencies.extend(newDependencies)
        for d in newDependencies:
            if d not in dependencies:
                dependencies.append(d)
    return dependencies


def getLibraryRetentionRate(lib: str):  # 7 / 8?
    add = len(list(db.wocConfirmedMigration.find(
        {"toLib": lib})))
    remove = len(list(db.wocConfirmedMigration.find(
        {"fromLib": lib})))
    return add/remove


if __name__ == '__main__':
    # print(getMigrationToCommits('org.json:json')[0])
    # print(type(getLibraryPublishTime("org.json:json")))
    # s = rrule.rrule(rrule.SECONDLY, dtstart=dateParser(
    #     "2010-12-21 17:46:08 UTC"), until=dateParser("2010-12-21 17:47:09 UTC")).count()
    # print(getAllDependencies("org.json", "json", "20160212"))
    print(getLibraryStayRate("org.json:json"))
