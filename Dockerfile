FROM continuumio/miniconda3:latest
MAINTAINER Mingxun Wang "mwang87@gmail.com"

WORKDIR /app
RUN apt-get update -y
RUN conda create -n usi -c rdkit rdkit
RUN /bin/bash -c "source activate usi"
RUN echo "source activate usi" > ~/.bashrc
RUN conda install -n usi -c anaconda flask
RUN conda install -n usi -c anaconda gunicorn
RUN conda install -n usi -c anaconda requests
RUN conda install -n usi -c bioconda spectrum_utils
RUN conda install -n usi -c conda-forge xmltodict
RUN conda install -n usi -c conda-forge qrcode
RUN conda install -n usi -c conda-forge requests-cache

RUN apt-get install -y libxrender-dev

COPY . /app
WORKDIR /app
