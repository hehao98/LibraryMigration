FROM continuumio/miniconda3


RUN conda install python=3.8 && \
    conda install nodejs -c conda-forge --repodata-fn=repodata.json && \
    conda install -c plotly plotly-orca

COPY requirements.txt /tmp/requirements.txt

RUN echo /tmp/requirements.txt && python -m pip install -r /tmp/requirements.txt

RUN jupyter labextension install jupyterlab-plotly@4.14.3
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager plotlywidget@4.14.3

EXPOSE 8888

VOLUME /app

WORKDIR /app

# this setup is not safe
CMD ["jupyter", "lab", "--allow-root", "--ip=0.0.0.0", "--no-browser", "--NotebookApp.token=''", "--NotebookApp.password=''"]