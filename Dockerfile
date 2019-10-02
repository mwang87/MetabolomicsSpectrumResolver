FROM continuumio/miniconda3:latest
MAINTAINER Mingxun Wang "mwang87@gmail.com"

WORKDIR /app
RUN apt-get update -y
RUN conda create -n rdkit -c rdkit rdkit
RUN /bin/bash -c "source activate rdkit"
RUN echo "source activate rdkit" > ~/.bashrc
RUN conda install -n rdkit -c anaconda flask
RUN conda install -n rdkit -c anaconda gunicorn
RUN conda install -n rdkit -c anaconda requests
RUN conda install -n rdkit -c bioconda spectrum_utils
RUN conda install -n rdkit -c conda-forge xmltodict
RUN conda install -n rdkit -c conda-forge qrcode
RUN conda install -n rdkit -c conda-forge requests-cache

COPY . /app
WORKDIR /app
