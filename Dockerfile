FROM continuumio/miniconda3:4.8.2
MAINTAINER Mingxun Wang "mwang87@gmail.com"

WORKDIR /app
RUN apt-get update -y && \
        apt-get install -y libxrender-dev && \
        apt-get install -y git-core
RUN conda create -y -n usi -c conda-forge -c bioconda -c defaults flask \
        gunicorn matplotlib numba numpy openssl qrcode rdkit requests \
        requests-cache scipy spectrum_utils werkzeug
RUN /bin/bash -c "source activate usi"
RUN pip install -e "git+git://github.com/berlinguyinca/spectra-hash.git@#egg=splash&subdirectory=python"
RUN echo "source activate usi" > ~/.bashrc

COPY . /app
WORKDIR /app
