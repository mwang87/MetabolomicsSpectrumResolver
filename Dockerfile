FROM ubuntu:22.04
MAINTAINER Mingxun Wang "mwang87@gmail.com"

WORKDIR /app
RUN apt-get update -y && \
        apt-get install -y libxrender-dev && \
        apt-get install -y git-core libarchive-dev build-essential wget vim curl

# Install Mamba
ENV CONDA_DIR /opt/conda
RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O ~/miniforge.sh && /bin/bash ~/miniforge.sh -b -p /opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH
RUN echo "export PATH=$CONDA_DIR:$PATH" >> ~/.bashrc

RUN mamba create -y -n usi -c conda-forge -c bioconda -c defaults celery==5.3.6 \
        dash=1.20.0 dash-bootstrap-components=0.9.2 flask gunicorn \
        joblib matplotlib==3.6.3 numba numpy openssl qrcode rdkit requests \
        requests-cache scipy spectrum_utils==0.3.5 werkzeug==2.0.0

# install redis with pypi
RUN /bin/bash -c 'source activate usi && pip install redis'

# installing hash
RUN /bin/bash -c 'source activate usi && pip install "git+https://github.com/berlinguyinca/spectra-hash.git#subdirectory=python" && pip install celery-once'

# installing analytics
RUN /bin/bash -c 'source activate usi && pip install umami-analytics'

RUN echo "source activate usi" > ~/.bashrc

COPY . /app
WORKDIR /app
