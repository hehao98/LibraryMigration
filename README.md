# Library Migration

This repository will be our main repository for our ongoing empirical paper about Java library migrations.
Note that for easy release and disposal in the future, we demand everything here must be written in English.
All files should not have any names so that we can just remove version control info for double blind review.

## Development

We use Anaconda and PyCharm Professional for development. 
Please configure your PyCharm to use a new Conda environment with Python 3.7+ and [requirements](requirements.txt) satisfied.

## Data Preparation

A dataset of library migration is already available [here](data/migrations.xlsx).
The more compact dataset of legal library migration rules is [here](data/rules.xlsx).
We use [this](get_issues.py) Python script to get issues and PRs [here](data/issues.xlsx).
