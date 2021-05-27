# Requirements

## Software Requirements

The software requirements for this replication package has already been described in the README and the `requirements.txt` file in this folder. We recommend to either exactly follow the installation commands to configure an Anaconda environment as follows, or to directly use the Docker Image. Although we have only tested our replication package on Ubuntu 20.04, it should also work in other common Linux distributions because we do not rely on any OS specific features.

```shell script
conda create -n LibraryMigration python=3.8
conda activate LibraryMigration
conda install nodejs -c conda-forge --repodata-fn=repodata.json
conda install -c plotly plotly-orca
python -m pip install -r requirements.txt
jupyter labextension install jupyterlab-plotly@4.14.3
jupyter labextension install @jupyter-widgets/jupyterlab-manager plotlywidget@4.14.3
```

For Plotly to function properly in `rq2_trend.ipynb`, you may also need to install X11 display server, using a command like `sudo apt-get install xvfb`.

## Hardware Requirements

We conduct development and execute all our experiments on a Ubuntu 20.04 server with two Intel Xeon Gold CPUs, 320GB memory, and 36TB RAID 5 Storage. We have also vetted this replication package in a Ubuntu 20.04 VirtualBox VM with 4 CPU Cores, 8GB Memory and 250GB storage. However, if the `cache/` folder is not included in the git repository, the notebooks will crash in this VirtualBox VM due to lack of memory. Therefore, in case the files in `cache/` need to be recomputed (e.g., when repurposing), we recommend to use this replication package in a commodity Linux server, with at least 16 CPU Cores, 64GB memory, and 250GB empty storage space.
