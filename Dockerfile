FROM continuumio/miniconda3:latest
MAINTAINER Mingxun Wang "mwang87@gmail.com"

WORKDIR /app
RUN apt-get update -y
RUN conda create -n usi -c rdkit rdkit=2019.09.3.0
RUN /bin/bash -c "source activate usi"
RUN echo "source activate usi" > ~/.bashrc
RUN conda install -n usi -c anaconda flask
RUN conda install -n usi -c anaconda gunicorn
RUN conda install -n usi -c anaconda requests
RUN conda install -n usi -c bioconda spectrum_utils
RUN conda install -n usi -c conda-forge xmltodict
RUN conda install -n usi -c conda-forge qrcode
RUN conda install -n usi -c conda-forge requests-cache
RUN conda install -n usi -c anaconda scipy

RUN apt-get install -y libxrender-dev
RUN /bin/bash -c "source activate usi && pip install 'git+git://github.com/berlinguyinca/spectra-hash.git@#egg=splash&subdirectory=python'"

COPY . /app
WORKDIR /app
