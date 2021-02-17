# R sucks for complex dataframe manipulations, move preprocessing stage here
import logging
import datautil
import numpy as np
import pandas as pd
import multiprocessing as mp
from collections import Counter


def simplify_license(s):
    if "LGPL" in s:
        return "LGPL"
    if "GPL" in s:
        return "GPL"
    if "EPL" in s:
        return "EPL"
    if "BSD" in s:
        return "BSD"
    if "Apache" in s:
        return "Apache"
    if "MIT" in s:
        return "MIT"
    if "JSON" in s:
        return "JSON"
    if s == "":
        return "No License"
    return "Other"


def get_indexes_to_remove(commit: str, df: pd.DataFrame) -> set:
    indexes = set()

    for row1 in df.itertuples(): 
        for row2 in df.itertuples():
            if row1.lib1 == row2.lib2 and row1.type == "rem" and row2.type == "add":
                indexes.add(row1.Index)
                indexes.add(row2.Index)
            if row1.Index < row2.Index and row1.type == row2.type:
                if row1.type == "rem" and row1.lib1 == row2.lib1:
                    indexes.add(row2.Index)
                if row1.type == "add" and row1.lib2 == row2.lib2:
                    indexes.add(row2.Index)
    return indexes


def run():
    data = pd.read_csv("cache/model_data.csv")
    logging.info(f"{len(data)} dep chgs, {len(data[data.type == 'add'])} adds, {len(data[data.type == 'rem'])} rems")

    migrations = datautil.select_migrations()
    commits = set(migrations.startCommit) | set(migrations.endCommit)
    libs = set(migrations.fromLib) | set(migrations.toLib)
    data = data[data.commit.isin(commits) & (data.lib1.isin(libs) | data.lib2.isin(libs))]
    logging.info(f"Mig only: {len(data)} dep chgs, {len(data[data.type == 'add'])} adds, {len(data[data.type == 'rem'])} rems")

    """
    with mp.Pool(mp.cpu_count()) as p:
        indexes = set.union(*p.starmap(get_indexes_to_remove, data.groupby("commit")))
    logging.info(f"{len(indexes)} dep chgs should be removed")
    data = data.drop(list(indexes), axis=0)
    logging.info(f"After dropping: {len(data)} dep chgs, {len(data[data.type == 'add'])} adds, {len(data[data.type == 'rem'])} rems")
    """

    data.release_freq = np.maximum(1, data.release_freq / 30)
    data.first_release_interval = data.first_release_interval / 365
    #data["last_release_2_year"] = (data.last_release_interval > (365 * 2)).map(int) 
    #data.last_release_interval = (data.last_release_interval / 30) / data.release_freq
    data.last_release_interval = np.maximum(0, data.last_release_interval / 365)
    
    data.vulnerabilities = np.minimum(1, data.vulnerabilities)

    data.in_other_file = data.in_other_file.map(int)
    data.in_trans_dep = data.in_trans_dep.map(int)

    data.license = data.license.fillna("").map(simplify_license)

    logging.info(Counter(data.license))

    data.to_csv("cache/model_data_r.csv", index=False)

    cls = pd.read_excel("data/cls2.xlsx")

    for cat in ["Logging", "JSON", "Testing"]:
        json_libs = set(cls[cls.adjusted_category == cat].package)
        data[data.lib1.isin(json_libs) | data.lib2.isin(json_libs)].to_csv(f"cache/model_data_{cat.lower()}_r.csv", index=False)
