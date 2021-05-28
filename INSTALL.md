# Install

## Replication Package Setup

We provide three different ways to replicate results in our paper. We will introduce them in detail in this section.

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

The easiest way to replicate results in our paper is to use the VirtualBox VM Image. First, download the VM Image from [this One Drive link](https://dreamok-my.sharepoint.com/:f:/g/personal/hehao_wowvv_com/EquUX-BJCjhOllxiNxA0ptkBDHTbDufze25oTK5SJOvlXg?e=bDJdUd) (we know it is non-persistent, so if it becomes unavailable, please use the other two ways for replication). After the download is finished, register and open this VM image. You should see a folder named `LibraryMigration` in the Desktop. Open this folder in Terminal and run `conda activate LibraryMigration && jupyter lab`. You should see a Jupyter Lab window automatically pop up, which you can use for replication.

### Using the Docker Image

To replicate our results with Docker, please ensure that you already have `docker`, `docker-compose`, `tar`, and `xz` installed in your Linux machine and you have access to Docker daemon (i.e., write permission to Docker socket). Please follow the following steps.

* First, download from Zenodo and extract `dbdata.tar.xz`; then move the extracted `dbdata` folder to the root directory of the git repository folder. 

* Then, by executing `cd docker && bash start.sh`, you should be able to set up two functional Docker containers (one for Jupyter Lab and one for MongoDB) in a few minutes. After the Docker finishes pulling images and setting up containers, a Jupyter Lab instance should be running at `http://localhost:8848`.  If you are working on Linux with a desktop environment, a Jupyter Lab window should automatically pop up. 

* Finally, change the MongoDB URL in `datautil.py` to `mongodb://mongo:27017` for the scripts to use the MongoDB container. 

If you run into any issues, we provide a more detailed setup and configuration guide in `docker/README.md`. Our Docker image may also work on Windows and macOS, but some special operations may be needed and we have only tested its functionality on Ubuntu 20.04. Please check the setup guide first when setting up our Docker image on Windows or macOS.

## Replicating Results

After the replication package is setup in any of the ways mentioned above, you should have a Jupyter Lab server instance running at `http://localhost:8888` (`http://localhost:8848`} if you use Docker, or some other URLs depending on your specific configuration). In Jupyter Lab, you should see the whole git repository folder, in which there are three notebooks: `rq1_prevalance.ipynb`, `rq2_trend.ipynb`, and `rq3_rationale.ipynb`. They correspond to the three RQs in the ESEC/FSE 2021 paper. You can directly see the plots and numbers used in our paper in the cells' output. For each notebook, you can start a Python kernel and run all cells, and then you should be able to replicate all the results in this notebook. The results should look identical or similar to the plots in the paper if it is working properly. For the migration graph, the automatically generated graph do not have a good layout, so we manually modified their layout by drag and dropping.
