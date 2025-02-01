SECRET_PATH ?= 'secret/scs/github/pat'
SECRET_TEMPFILE ?= ./.secrets
CONTAINER_RT ?= sudo podman
REPO ?= slaclab/status-pusher
TAG ?= latest
#GIT_TOKEN ?= '<GIT_TOKEN NOT PROVIDED>'
CONTAINER_REGISTRY ?= localhost

default: pytest test_promq

pytest:
	echo "running pytest module"
	./.venv/bin/python3 -m pytest ./test

secrets:
	mkdir -p ./.secrets
	set -e; for i in s3df-status-pusher; do vault kv get --field=$$i $(SECRET_PATH) > $(SECRET_TEMPFILE)/$$i ; done

clean-secrets:
	rm -rf $(SECRET_TEMPFILE)

venv:
	mkdir -p .venv
	python3 -m venv ./.venv

pip:
	./.venv/bin/pip3 install --upgrade pip
	./.venv/bin/pip3 install -r requirements.txt

black:
	# discuss before applying to status_pusher.py
	./.venv/bin/black ./
	./.venv/bin/black ./test/

clean-all: clean-secrets
	rm -rf .venv/
	rm -rf __pycache__
	rm pyvenv.cfg
	rm pip-selfcheck.json

build:
	$(CONTAINER_RT) build -t $(CONTAINER_REGISTRY)/$(REPO):$(TAG) .

build_and_run_interactive: build
	$(CONTAINER_RT) run -it $(CONTAINER_REGISTRY)/$(REPO):$(TAG) bash

push:
	@printf "\n################################################################################"
	@printf "\nImages are built and published automatically upon pushing the 'release' branch".
	@printf "\n\nView them at:"
	@printf "\nhttps://github.com/slaclab/status-pusher/pkgs/container/status-pusher"
	@printf "\n\nPull them from:"
	@printf "\ndocker://ghcr.io/ghcr.io/slaclab/status-pusher"
	@printf "\n################################################################################\n\n"

#registry_login:
#	$(CONTAINER_RT) login $(CONTAINER_REGISTRY)/$(REPO)
#
#push: build
#	echo "Note: this should be run with sudo on iana after logging into docker.com\
#	using creds at /secret/dockerhub/slaclab/credentials"
#	$(CONTAINER_RT) push $(CONTAINER_REGISTRY)/$(REPO):$(TAG)

################################
# live tests against github repo
################################
test_promq::
	echo "Running Live (read-only) test against real influxdb server and repo on github.com"
	STATUS_PUSHER_GIT_URL='https://github.com/slaclab/s3df-status' \
	STATUS_PUSHER_PROMQ_URL='https://prometheus.slac.stanford.edu' \
	STATUS_PUSHER_QUERY='avg( avg_over_time(nmap_port_state{service=`ssh`,group=`s3df`}[5m]) )' \
	STATUS_PUSHER_FILEPATH=public/status/test_report.log \
	STATUS_PUSHER_GIT_BRANCH='test_branch' \
	./.venv/bin/python3 status_pusher.py promq

test_influxdb::
	echo "Running Live (read-only) test against real Prometheus server and repo on github.com"
	STATUS_PUSHER_GIT_URL='https://github.com/slaclab/s3df-status' \
	STATUS_PUSHER_INFLUXQ_URL='https://influxdb.slac.stanford.edu' \
	STATUS_PUSHER_INFLUXQ_DB_NAME='slurm' \
	STATUS_PUSHER_QUERY='SELECT last("jobs") FROM "squeue" WHERE (("state" =~ /^RUNNING$/) AND ("partition" =~ /^(ada|ampere|ampere_roma_milano|milano|milano_roma|milano_roma_ampere|roma|roma_ampere_milano|roma_milano|roma_milano_ampere|test|testweka|turing)$/)) LIMIT 1' \
	STATUS_PUSHER_FILEPATH=public/status/test_report.log \
	STATUS_PUSHER_GIT_BRANCH='test_branch' \
	./.venv/bin/python3 status_pusher.py influxq

test-push: secrets
	echo "Running Live (read-write) test that will push to real repo on github.com"
	STATUS_PUSHER_GIT_URL='https://github.com/slaclab/s3df-status' \
	STATUS_PUSHER_PROMQ_URL='https://prometheus.slac.stanford.edu' \
	STATUS_PUSHER_QUERY='avg( avg_over_time(nmap_port_state{service=`ssh`,group=`s3df`}[5m]) )' \
	STATUS_PUSHER_FILEPATH=public/status/test_report.log \
	STATUS_PUSHER_GIT_BRANCH='test_branch' \
	STATUS_PUSHER_GIT_PUSH_URL='https://$(shell cat $(SECRET_TEMPFILE)/s3df-status-pusher)@github.com/slaclab/s3df-status' \
	./.venv/bin/python3 status_pusher.py promq
