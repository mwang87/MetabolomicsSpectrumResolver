FROM ubuntu:22.04
LABEL maintainer="Mingxun Wang <mwang87@gmail.com>"

WORKDIR /app
RUN apt-get update -y && \
        apt-get install -y libxrender-dev && \
        apt-get install -y git-core libarchive-dev build-essential wget vim curl

# Install Mamba
ENV CONDA_DIR=/opt/conda
RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O ~/miniforge.sh && /bin/bash ~/miniforge.sh -b -p /opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH
RUN echo "export PATH=$CONDA_DIR:$PATH" >> ~/.bashrc

# Ensure packages resolve only from conda-forge/bioconda (no defaults/anaconda).
RUN mamba config --system --set channel_priority strict && \
        mamba config --system --set show_channel_urls true && \
        mamba config --system --remove channels defaults || true

RUN mamba create -y -n usi -c conda-forge -c bioconda celery==5.3.6 \
        dash=1.20.0 dash-bootstrap-components=0.9.2 flask gunicorn \
        joblib matplotlib==3.6.3 numba numpy openssl qrcode rdkit requests \
        requests-cache scipy setuptools spectrum_utils==0.3.5 werkzeug==2.0.0 \
        flask-limiter flask-cors \
        python=3.11


# install redis with pypi
RUN /bin/bash -c 'source activate usi && pip install redis "setuptools<81"'

# installing hash
RUN /bin/bash -c 'source activate usi && pip install "git+https://github.com/berlinguyinca/spectra-hash.git#subdirectory=python" && pip install celery-once'

# installing analytics
RUN /bin/bash -c 'source activate usi && pip install umami-analytics'

RUN echo "source activate usi" > ~/.bashrc

COPY . /app
WORKDIR /app
