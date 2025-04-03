SECRET_PATH ?= 'secret/scs/github/pat'
SECRET_TEMPFILE ?= ./.secrets
CONTAINER_RT ?= sudo podman
REPO ?= slaclab/status-pusher
TAG ?= latest
#GIT_TOKEN ?= '<GIT_TOKEN NOT PROVIDED>'
CONTAINER_REGISTRY ?= localhost

default: pytest

lint:
	pylint status_pusher.py

debug: pytest-debug test_promq test_influxdb

coverage_html:
	echo "running pytest with html coverage output"
	./.venv/bin/pytest --cov=status_pusher ./ --cov-report html

pytest-debug:
	echo "running pytest with coverage and console output"
	# -s to output standard console output (eg print stmts)
	./.venv/bin/pytest -s --cov=status_pusher --cov-report term-missing ./ 
 
pytest:
	echo "running pytest with coverage (no console output)"
	./.venv/bin/pytest -v --cov=status_pusher --cov-report term-missing ./ 

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
	./.venv/bin/black ./

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
# NOTE STATUS_PUSHER_GIT_BRANCH is NOT Implemented.
# `main` branch will always be used
################################
test_promq::
	echo "Running Live (read-only) test against real influxdb server and repo on github.com"
	STATUS_PUSHER_GIT_URL='https://github.com/slaclab/s3df-status' \
	STATUS_PUSHER_PROMQ_URL='https://prometheus.slac.stanford.edu' \
	STATUS_PUSHER_QUERY='avg( avg_over_time(nmap_port_state{service=`ssh`,group=`s3df`}[5m]) )' \
	STATUS_PUSHER_FILEPATH=public/status/test_report.log \
	STATUS_PUSHER_GIT_BRANCH='main' \
	./.venv/bin/python3 status_pusher.py promq

test_influxdb::
	echo "Running Live (read-only) test against real Prometheus server and repo on github.com"
	STATUS_PUSHER_GIT_URL='https://github.com/slaclab/s3df-status' \
	STATUS_PUSHER_INFLUXQ_URL='https://influxdb.slac.stanford.edu' \
	STATUS_PUSHER_INFLUXQ_DB_NAME='telegraf' \
	STATUS_PUSHER_QUERY="SELECT mean(\"status_code\") FROM \"monit_process\" WHERE (\"service\" = 'slurmctld' OR \"service\" = 'slurmdbd') AND time > now()-5m GROUP BY \"service\" ;" \
	STATUS_PUSHER_FILEPATH=public/status/test_report.log \
	STATUS_PUSHER_GIT_BRANCH='main' \
	./.venv/bin/python3 status_pusher.py influxq

test-push: secrets
	echo "Running Live (read-write) test that will push to real repo on github.com"
	STATUS_PUSHER_GIT_URL='https://github.com/slaclab/s3df-status' \
	STATUS_PUSHER_PROMQ_URL='https://prometheus.slac.stanford.edu' \
	STATUS_PUSHER_QUERY='avg( avg_over_time(nmap_port_state{service=`ssh`,group=`s3df`}[5m]) )' \
	STATUS_PUSHER_FILEPATH=public/status/test_report.log \
	STATUS_PUSHER_GIT_BRANCH='main' \
	STATUS_PUSHER_GIT_PUSH_URL='https://$(shell cat $(SECRET_TEMPFILE)/s3df-status-pusher)@github.com/slaclab/s3df-status' \
	./.venv/bin/python3 status_pusher.py promq

generate-test-data:
	.venv/bin/python3 test/util/generate_fake_test_data.py
