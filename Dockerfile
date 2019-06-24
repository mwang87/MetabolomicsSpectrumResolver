FROM ubuntu:16.04
MAINTAINER Mingxun Wang "mwang87@gmail.com"

RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential

RUN pip3 install urllib3==1.23
RUN pip3 install flask
RUN pip3 install requests
RUN pip3 install requests-cache
RUN pip3 install gunicorn
RUN pip3 install xmltodict

COPY . /app
WORKDIR /app
