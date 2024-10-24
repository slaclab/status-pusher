CONTAINER_RT ?= podman
REPO ?= slaclab/status-pusher
TAG ?= latest

venv:
	python3 -m venv .

pip:
	./bin/pip3 install -r requirements.txt

clean:
	rm -rf bin include lib  lib64

build:
	$(CONTAINER_RT) build -t $(REPO):$(TAG) .

push:
	$(CONTAINER_RT) push $(REPO):$(TAG)
 
test:
	STATUS_PUSHER_PROMETHEUS_URL='https://prometheus.slac.stanford.edu' STATUS_PUSHER_QUERY='nmap_port_state{service=`ssh`,group=`s3df`}' ./bin/python3 status-pusher.py
