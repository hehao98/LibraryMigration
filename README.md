# Library Migration

This repository will be our main repository for our ongoing empirical paper about Java library migrations.
Note that for easy release and disposal in the future, we demand everything here must be written in English.
All files should not have any names so that we can just remove version control info for double blind review.

## Development

We use Anaconda for development. 
Please configure to use a new Conda environment with Python 3.8 and [requirements](requirements.txt) satisfied.

```shell script
conda create -n LibraryMigration python=3.8
conda activate LibraryMigration
conda install nodejs -c conda-forge --repodata-fn=repodata.json
conda install -c plotly plotly-orca
python -m pip install -r requirements.txt
jupyter labextension install jupyterlab-plotly@4.14.3
jupyter labextension install @jupyter-widgets/jupyterlab-manager plotlywidget@4.14.3
```

## Data Preparation

A dataset of library migration is already available [here](data/migrations.xlsx).
The more compact dataset of legal library migration rules is [here](data/rules.xlsx).
We use [get_issues.py](get_prs_by_commits.py) Python script to get issues and PRs [here](data/prs.xlsx).
We then use [get_coding_data.py](get_coding_data.py) to aggregate coding data [here](data/coding_commits_prs.xlsx).

The final coding is done entirely manually in [this file](data/coding.xlsx).

## Docker

Note: this may take hours to finish.

```
docker build -f dockerfile-mongodb -t mongodb-lm .
docker build -f dockerfile-jupyter -t jupyter-lm .
docker run --name mongodb-lm -d mongodb-lm --wiredTigerCacheSizeGB 2
docker run -dp 12344:12344 jupyter-lm --network mongo
```
