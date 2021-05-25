# Replication Pacakge for ESEC/FSE 2021 Paper "A Large-Scale Empirical Study of Java Library Migrations: Prevalence, Trends, and Rationales"

This repository will be our main repository for our ongoing empirical paper about Java library migrations.
Note that for easy release and disposal in the future, we demand everything here must be written in English.
All files should not have any names so that we can just remove version control info for double blind review.

## Initialize Development Environment

First, create the following folders in the git repository: `mkdir plots && mkdir cache`

### Anaconda

We use Anaconda for configuring Python development. 
Please configure to use a new Conda environment by executing the following commands, step by step.

```shell script
conda create -n LibraryMigration python=3.8
conda activate LibraryMigration
conda install nodejs -c conda-forge --repodata-fn=repodata.json
conda install -c plotly plotly-orca
python -m pip install -r requirements.txt
jupyter labextension install jupyterlab-plotly@4.14.3
jupyter labextension install @jupyter-widgets/jupyterlab-manager plotlywidget@4.14.3
```

### MongoDB

Some of the data comes from our previous [SANER 2021](https://doi.org/10.1109/SANER50967.2021.00016) paper, which is stored in MongoDB. 
We ship all the necessary database dumps in our artifact in a folder called `dbdump`.
First, you have to install MongoDB in your computer and have it listening at `mongodb:://localhost:27017` without any authentication.
Then, you can use `cd dbdump && bash mongodb_restore.sh` to restore the necessary data in the `migration_helper` database.
You can check the schema of each collection using MongoDB Compass, and refer to the documentation folder if necessary.

## Data Preparation

A dataset of library migration is already available [here](data/migrations.xlsx).
The more compact dataset of legal library migration rules is [here](data/rules.xlsx).
We use [get_issues.py](get_prs_by_commits.py) Python script to get issues and PRs [here](data/prs.xlsx).
We then use [get_coding_data.py](get_coding_data.py) to aggregate coding data [here](data/coding_commits_prs.xlsx).

The final coding is done entirely manually in [this file](data/coding.xlsx).
