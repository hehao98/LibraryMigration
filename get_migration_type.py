import logging
import semver
import datautil
import multiprocessing as mp
import pandas as pd


def get_migration_type(from_lib: str, to_lib: str) -> str:
    fgid, faid = from_lib.split(":")
    tgid, taid = to_lib.split(":")
    

    if len(set(faid.split("-")) & set(taid.split("-")) - {"api", "core", "all"}) != 0:  # seems like rename
        fversions = set(x["version"]
                        for x in datautil.select_library_versions(from_lib))
        tversions = set(x["version"]
                        for x in datautil.select_library_versions(to_lib))
        print(sorted(fversions))
        print(sorted(tversions))
        if len(fversions & tversions) == 0:
            try:
                if semver.compare(
                        sorted(fversions)[-1], sorted(tversions)[-1]) == -1:
                    return "rename:upgrade"
                else:
                    return "rename:downgrade"
            except Exception as ex:
                logging.info(ex)
        return "rename:undecided"
    return "undecided"


def run():
    libraries = datautil.select_libraries()
    rules = datautil.select_rules(set(libraries.name))
    with mp.Pool(mp.cpu_count() // 2) as pool:
        rules["type"] = pool.starmap(
            get_migration_type, zip(
                rules["fromLib"], rules["toLib"]))
    print(rules)
    rules.to_csv("rules.csv", index=False)


if __name__ == "__main__":
    print(
        get_migration_type(
            "log4j:log4j",
            "org.apache.logging.log4j:log4j-api"))
    print(
        get_migration_type(
            "org.apache.logging.log4j:log4j-api",
            "log4j:log4j"))
    print(
        get_migration_type(
            "commons-httpclient:commons-httpclient",
            "org.apache.httpcomponents:httpclient"))
