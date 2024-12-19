FROM python:3.12-slim

RUN mkdir /app
ADD status_pusher.py /app/
ADD requirements.txt /app/requirements.txt
RUN ln -s /app/status_pusher.py /usr/bin/status_pusher

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install git

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt && rm /app/requirements.txt
