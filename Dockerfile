FROM python:3.12-slim

RUN mkdir /app
ADD status_pusher.py /app/
ADD requirements.txt /app/requirements.txt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt && rm /app/requirements.txt
