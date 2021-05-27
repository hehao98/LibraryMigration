# Replication Package for ESEC/FSE 2021 Paper "A Large-Scale Empirical Study of Java Library Migrations: Prevalence, Trends, and Rationales"

This is the replication package for our ESEC/FSE 2021 paper *A Large-Scale Empirical Study on Java Library Migrations: Prevalence, Trends, and Rationales*.  It can be used to replicate all three research questions in the paper using our preprocessed and manually labeled data.  It consists of a git repository and a MongoDB database dump. By properly configuring a MongoDB database server and an Anaconda environment, a person can easily replicate the results in our paper by re-running the provided Jupyter Notebooks. We hope the provided scripts and dataset can be used to facilitate further research. The replication package have been permanently archived at https://doi.org/10.5281/zenodo.4816753.

## Introduction

With the rise of open-source software and package hosting platforms, reusing 3rd-party libraries has become a common practice. Due to risks including security vulnerabilities, lack of maintenance, unexpected failures, and license issues, a project may completely remove a used library and replace it with another library, which we call *library migration*. Despite substantial research on dependency management, the understanding of how and why library migrations occur is still lacking.  Achieving this understanding may help practitioners optimize their library selection criteria, develop automated approaches to monitor dependencies, and provide migration suggestions for their libraries or software projects. To bridge this knowledge gap, we ask the following three research questions in our ESEC/FSE 2021 paper:

* **RQ1:** How common are library migrations?
* **RQ2:** How do migrations happen between libraries?
* **RQ3:** What are the frequently mentioned reasons by developers when they conduct a library migration?

To answer the research questions, we reuse the MongoDB database from our previous paper [1], compute dependency changes and library migrations as defined in the ESEC/FSE 2021 paper, and conduct manual labelling, exploratory data analysis, data visualization and thematic analysis to generate the presented results. The detailed results can be found in our paper. We implement all automated processing using Python in an Anaconda environment and we conduct all manual labelling using Microsoft Excel. We hope the scripts and dataset in this replication package can be leveraged to facilitate further studies in library migration and other related fields.  We intend to claim the **Artifacts Available** badge and the **Artifacts Evaluated - Reusable** badge for our replication package. 

## Required Skills and Environment

We expect a person to have a reasonable amount of knowledge on git, Linux, Python, Anaconda, Jupyter Lab, MongoDB, and some experience with Python data science development, in order to make the best use of this replication package. 

We provide several ways of replication for different usage scenarios. You can choose the way that suits you best.

* First, for reuse and further development, we recommend to manually setup the required environment in a commodity Linux server with at least 16 CPU Cores, 64GB memory, and 250GB empty storage space.
* Second, for easy one-click replication, we provide a Ubuntu 20.04 VirtualBox VM Image in which the replication package has already been properly configured. This VM Image can be opened with VirtualBox 6.1 (or later versions) in any supported machine with at least 8GB of memory and 4 CPU Cores allocated for this VM. 
* Finally, for those who are familiar with Docker, we provide a Docker image which can be readily deployed and reused in a Linux machine with Docker environment. The hardware requirements for this Docker image is similar to that of the manual setup.

## Replication Package Setup

As mentioned in the previous section, we provide three different ways to replicate results in our paper. We will introduce them in detail in this section.

If you do not use the VirtualBox VM image, please first clone this git repository (or download the repository archive from Zenodo). Create the following folder in this git repository, if they do not exist already: `mkdir plots`. Download and unzip `cache.zip`; then copy the extracted `cache` folder into the git repository folder. This `cache/` folder contains some precomputed data which can greatly speed up replication (otherwise re-running the notebooks will be very computation intensive).

### Setup Environment Manually

We use Anaconda for Python development, so please configure to use a new Conda environment by executing the following commands step by step.

```shell script
conda create -n LibraryMigration python=3.8
conda activate LibraryMigration
conda install nodejs -c conda-forge --repodata-fn=repodata.json
conda install -c plotly plotly-orca
python -m pip install -r requirements.txt
jupyter labextension install jupyterlab-plotly@4.14.3
jupyter labextension install @jupyter-widgets/jupyterlab-manager plotlywidget@4.14.3
```

Then, download (from Zenodo) and unzip the `dbdump.zip` and configure a latest MongoDB server listening at `localhost:27017` without any authentication. Run `cd dbdump && bash mongodb_restore.sh` to restore the necessary data in the `migration_helper` database (this may take some time to finish). You can check the schema of each collection using MongoDB Compass, and refer to the documentations if necessary. You may also use a different MongoDB URL but you have to modify `mongodb_restore.sh` and `datautil.py` accordingly. After all the MongoDB collections have been restored, you can activate the `LibraryMigration` environment and run `jupyter lab` in the repository folder for replication.

For Plotly to function properly in `rq2_trend.ipynb`, you may also need to install X11 display server, using a command like `sudo apt-get install xvfb`.

### Using the VirtualBox VM Image

The easiest way to replicate results in our paper is to use the VirtualBox VM Image. First, download the VM Image from [this Google Drive link]{TODO: Add Link} (we know it is non-persistent, so if it becomes unavailable, please use the other two ways for replication). After the download is finished, register and open this VM image. You should see a folder named `LibraryMigration` in the Desktop. Open this folder in Terminal and run `conda activate LibraryMigration && jupyter lab`. You should see a Jupyter Lab window automatically pop up, which you can use for replication.

### Using the Docker Image

To replicate our results with Docker, please ensure that you already have `docker`, `docker-compose`, `tar`, and `xz` installed in your Linux machine and you have access to Docker daemon (i.e., write permission to Docker socket). Please follow the following steps.

* First, download from Zenodo and extract `dbdata.tar.xz`; then move the extracted `dbdata` folder to the root directory of the git repository folder. 
* Then, by executing `cd docker && bash start.sh`, you should be able to set up two functional Docker containers (one for Jupyter Lab and one for MongoDB) in a few minutes. After the Docker finishes pulling images and setting up containers, a Jupyter Lab instance should be running at `http://localhost:8848`.  If you are working on Linux with a desktop environment, a Jupyter Lab window should automatically pop up. 
* Finally, change the MongoDB URL in `datautil.py` to `mongodb://mongo:27017` for the scripts to use the MongoDB container. 

If you run into any issues, we provide a more detailed setup and configuration guide in `docker/README.md`. Our Docker image may also work on Windows and macOS, but some special operations may be needed and we have only tested its functionality on Ubuntu 20.04. Please check the setup guide first when setting up our Docker image on Windows or macOS.

## Replicating Results

After the replication package is setup in any of the ways mentioned above, you should have a Jupyter Lab server instance running at `http://localhost:8888` (`http://localhost:8848` if you use Docker, or some other URLs depending on your specific configuration). In Jupyter Lab, you should see the whole git repository folder, in which there are three notebooks: `rq1_prevalance.ipynb`, `rq2_trend.ipynb`, and `rq3_rationale.ipynb`. They correspond to the three RQs in the ESEC/FSE 2021 paper. You can directly see the plots and numbers used in our paper in the cells' output. For each notebook, you can start a Python kernel and run all cells, and then you should be able to replicate all the results in this notebook. The results should look identical or similar to the plots in the paper if it is working properly. For the migration graph, the automatically generated graph do not have a good layout, so we manually modified their layout by drag and dropping.

## Additional Documentation

### How We Obtained Files in this git Repository

In this section, we explain files in this repository and how we obtained these files. However, the process described here requires significant amount of manual work, so this section cannot be used as replication instructions. Instead, it can serve as a reference if you want to reuse/repurpose the scripts and data in this repository for further studies. 

The process is summarized in the following figure.


### Some Ready-To-Use Dataset

We also have some ready-to-use dataset that is largely self-explanatory and can be easily used for further studies.

First, we have a dataset of manually confirmed library migrations [here](data/migrations.xlsx) and a more compact dataset of library migration rules is [here](data/rules.xlsx). We use [get_issues.py](get_prs_by_commits.py) Python script to get the related issues and PRs [here](data/prs.xlsx). We then use [get_coding_data.py](get_coding_data.py) to aggregate coding data [here](data/coding_commits_prs.xlsx). The final coding is done entirely manually in [this file](data/coding.xlsx).

Second, we have the list of dependency changes, libraries, repositories, and migration graphs in the `cache/` folder in CSV or JSON format. These files should be largely self-explanatory.

Finally, the MongoDB data dump used in the SANER 2021 paper contains a variety of preprocessed GitHub repository and Maven artifact data, with accompanying documentations in the `doc/` folder. Note that the `dbdump.zip` file provided in Zenodo does not contain all collections due to space limitations, but the provided collections are sufficient for replicating results in this paper.

## References

1. Hao He, Yulin Xu, Yixiao Ma, Yifei Xu, Guangtai Liang, and Minghui Zhou. 2021. A multi-metric ranking approach for library migration recommendations. In 2021 IEEE International Conference on Software Analysis, Evolution and Reengineering (SANER). IEEE, 72–83.

