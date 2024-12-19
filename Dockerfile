FROM python:3.12-slim

RUN mkdir /app
ADD status_pusher.py /app/
ADD requirements.txt /app/requirements.txt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt && rm /app/requirements.txt

#RUN apt-get update && apt-get install -y nmap && apt-get autoclean && apt-get autoremove && rm -rf /var/lib/apt/lists/* && rm -rf /var/cache
