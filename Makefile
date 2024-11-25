SECRET_PATH ?= 'secret/scs/github/pat'
SECRET_TEMPFILE ?= ./.secrets
CONTAINER_RT ?= podman
REPO ?= slaclab/status-pusher
TAG ?= latest
#GIT_TOKEN ?= '<GIT_TOKEN NOT PROVIDED>'

default: test

secrets:
	mkdir -p ./.secrets
	set -e; for i in s3df-status-pusher; do vault kv get --field=$$i $(SECRET_PATH) > $(SECRET_TEMPFILE)/$$i ; done

clean-secrets:
	rm -rf $(SECRET_TEMPFILE)

venv:
	python3 -m venv .

pip:
	./bin/pip3 install --upgrade pip
	./bin/pip3 install -r requirements.txt

clean-all: clean-secrets
	rm -rf bin include lib lib64 share

build:
	$(CONTAINER_RT) build -t $(REPO):$(TAG) .

push:
	$(CONTAINER_RT) push $(REPO):$(TAG)

################################
# live tests against github repo
################################
test::
	STATUS_PUSHER_GIT_URL='https://github.com/slaclab/s3df-status' \
	STATUS_PUSHER_PROMETHEUS_URL='https://prometheus.slac.stanford.edu' \
	STATUS_PUSHER_QUERY='avg( avg_over_time(nmap_port_state{service=`ssh`,group=`s3df`}[5m]) )' \
	STATUS_PUSHER_FILEPATH=public/status/test_report.log \
	STATUS_PUSHER_GIT_BRANCH='test_branch' \
	./bin/python3 status-pusher.py

test-push: secrets
	STATUS_PUSHER_GIT_URL='https://github.com/slaclab/s3df-status' \
	STATUS_PUSHER_PROMETHEUS_URL='https://prometheus.slac.stanford.edu' \
	STATUS_PUSHER_QUERY='avg( avg_over_time(nmap_port_state{service=`ssh`,group=`s3df`}[5m]) )' \
	STATUS_PUSHER_FILEPATH=public/status/test_report.log \
	STATUS_PUSHER_GIT_BRANCH='test_branch' \
	STATUS_PUSHER_GIT_PUSH_URL='https://$(shell cat $(SECRET_TEMPFILE)/s3df-status-pusher)@github.com/slaclab/s3df-status' \
    echo $(STATUS_PUSHER_GIT_PUSH_URL) \
	#./bin/python3 status-pusher.py
