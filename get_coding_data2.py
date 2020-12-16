import pandas as pd
from collections import defaultdict


def run():
    data = pd.read_excel("data/coding.xlsx").drop_duplicates(["type", "link"]).fillna("")
    migrations = pd.read_excel("data/migrations.xlsx")
    issues = pd.read_excel("data/issues.xlsx")
    prs = pd.read_excel("data/prs.xlsx")

    link_to_migrations = defaultdict(set)
    for idx, row in migrations.iterrows():
        link_to_migrations[row["startCommit"]].add((row["fromLib"], row["toLib"]))
        link_to_migrations[row["endCommit"]].add((row["fromLib"], row["toLib"]))

    for idx, row in prs.iterrows():
        link_to_migrations[(row["repoName"], row["number"])] = set(link_to_migrations[row["relatedCommit"]])

    for idx, row in issues.iterrows():
        repo_name = row["sourceLink"].split("/")[3] + "/" + row["sourceLink"].split("/")[4]
        number = row["sourceLink"].split("/")[6]
        if "commit" in row["sourceLink"]:
            link_to_migrations[(row["repoName"], row["number"])] = set(link_to_migrations[number])
        else:
            link_to_migrations[(row["repoName"], row["number"])] = set(link_to_migrations[(repo_name, int(number))])

    for idx, row in data.iterrows():
        repo_name = row["link"].split("/")[3] + "/" + row["link"].split("/")[4]
        number = row["link"].split("/")[6]
        if row["type"] == "commit":
            pairs = list(sorted(link_to_migrations[number]))
        else:
            pairs = list(sorted(link_to_migrations[(repo_name, int(number))]))
        data.loc[idx, "fromLib"] = "\n".join(x for x, y in pairs)
        data.loc[idx, "toLib"] = "\n".join(y for x, y in pairs)

    data.to_excel("data/coding2.xlsx", index=False)
