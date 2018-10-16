# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

SHELL := /bin/bash

.PHONY: clean misspell

PREFIX := $(shell pwd)

DEV_PREFIX ?= $(PREFIX)
DEV_PREFIX := $(shell cd $(DEV_PREFIX); pwd)

# GCLOUD_ZIP_NAME and GCLOUD_ZIP_HREF are independent but should be
# updated together to ensure update is forced during `vagrant provision`
GCLOUD_ZIP_HREF=https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-154.0.1-linux-x86_64.tar.gz
GCLOUD_ZIP_NAME=google-cloud-sdk-154.0.1-linux-x86_64.tar.gz
GCLOUD_ZIP_PATH=$(DEV_PREFIX)/opt/$(GCLOUD_ZIP_NAME)
GCLOUD_SDK_PATH=$(DEV_PREFIX)/opt/google-cloud-sdk

APPENGINE_PACKAGES_DIR=$(DEV_PREFIX)/opt/gae_packages

APPENGINE_ENV_DIR=$(DEV_PREFIX)/opt/gae_virtualenv
APPENGINE_REQUIREMENTS_TXT=$(PREFIX)/src/requirements.txt

STATIC_PATH=$(PREFIX)/src/ggrc/static
NODE_MODULES_PATH=$(DEV_PREFIX)/node_modules
GOLANG_PATH=/vagrant-dev/golang
GOLANG_BIN=$(GOLANG_PATH)/go/bin/go
GOLANG_PACKAGES=$(GOLANG_PATH)/bin

$(GCLOUD_SDK_PATH) : $(GCLOUD_ZIP_PATH)
	cd `dirname $(GCLOUD_SDK_PATH)`; \
		tar -xzf $(GCLOUD_ZIP_PATH)

gcloud_sdk : $(GCLOUD_SDK_PATH)

clean_gcloud_sdk :
	rm -rf -- "$(GCLOUD_SDK_PATH)"
	rm -f "$(GCLOUD_ZIP_PATH)"

$(GCLOUD_ZIP_PATH) :
	mkdir -p `dirname $(GCLOUD_ZIP_PATH)`
	wget "$(GCLOUD_ZIP_HREF)" -O "$(GCLOUD_ZIP_PATH).tmp"
	mv "$(GCLOUD_ZIP_PATH).tmp" "$(GCLOUD_ZIP_PATH)"

appengine_sdk : $(GCLOUD_SDK_PATH)
	yes | "$(GCLOUD_SDK_PATH)/bin/gcloud" components install app-engine-python

clean_appengine_packages :
	rm -rf -- "$(APPENGINE_PACKAGES_DIR)"
	rm -rf -- "$(APPENGINE_ENV_DIR)"

$(APPENGINE_ENV_DIR) :
	mkdir -p `dirname $(APPENGINE_ENV_DIR)`
	virtualenv "$(APPENGINE_ENV_DIR)"
	source "$(APPENGINE_ENV_DIR)/bin/activate"; \
		pip install -U pip==9.0.1; \

appengine_virtualenv : $(APPENGINE_ENV_DIR)

$(APPENGINE_PACKAGES_DIR) : $(APPENGINE_ENV_DIR)
	mkdir -p $(APPENGINE_PACKAGES_DIR)
	source "$(APPENGINE_ENV_DIR)/bin/activate"; \
		pip install --no-deps -r "$(APPENGINE_REQUIREMENTS_TXT)" --target "$(APPENGINE_PACKAGES_DIR)"
	cd "$(APPENGINE_PACKAGES_DIR)"; \
		find . -name "*.pyc" -delete; \
		find . -name "*.egg-info" | xargs rm -rf

appengine_packages : $(APPENGINE_PACKAGES_DIR)

appengine : appengine_sdk appengine_packages

clean_appengine : clean_gcloud_sdk clean_appengine_packages


## Local environment


$(DEV_PREFIX)/opt/dev_virtualenv :
	mkdir -p $(DEV_PREFIX)/opt/dev_virtualenv
	virtualenv $(DEV_PREFIX)/opt/dev_virtualenv

dev_virtualenv : $(DEV_PREFIX)/opt/dev_virtualenv

dev_virtualenv_packages : dev_virtualenv src/requirements-dev.txt src/requirements.txt  src/requirements-selenium.txt
	source "$(PREFIX)/bin/init_env"; \
		pip install -U pip==9.0.1; \
		pip install --no-deps -r src/requirements.txt; \
		pip install -r src/requirements-dev.txt; \
		pip install -r src/requirements-selenium.txt

linked_packages : dev_virtualenv_packages
	mkdir -p $(DEV_PREFIX)/opt/linked_packages
	source bin/init_env; \
		setup_linked_packages.py $(DEV_PREFIX)/opt/linked_packages

golang_packages : export GOPATH=$(GOLANG_PATH)
golang_packages : export GOROOT=$(GOLANG_PATH)/go
golang_packages :
	mkdir -p $(GOLANG_PATH)
	wget https://storage.googleapis.com/golang/go1.6.3.linux-amd64.tar.gz -O $(GOLANG_PATH)/go.tar.gz
	tar -C $(GOLANG_PATH) -xzf $(GOLANG_PATH)/go.tar.gz
	rm $(GOLANG_PATH)/go.tar.gz
	$(GOLANG_BIN) get -u github.com/client9/misspell/cmd/misspell

setup_dev : dev_virtualenv_packages linked_packages golang_packages

misspell :
	find . -type f -name "*" \
		! -path "*/.*"\
		! -path "./node_modules/*"\
		! -path "./tmp/*"\
		! -path "./*.sql"\
		! -path "./*.zip"\
		! -path "./*.png"\
		! -path "./*.gz"\
		! -path "./*.ini"\
		! -path "./venv/*"\
		! -path "./src/ggrc/static/*"\
		! -path "./src/ggrc-client/vendor/*"\
		! -path "./test/*.out"\
		! -path "./test/*.xml"\
		! -path "./src/ggrc/assets/stylesheets/dashboard.css"\
		! -path "./src/packages/*"\
		! -path "./package-lock.json"\
		| xargs $(GOLANG_PACKAGES)/misspell -error -locale US

## Deployment!

src/ggrc/assets/assets.manifest :
	source "bin/init_env"; \
		GGRC_SETTINGS_MODULE="$(SETTINGS_MODULE)" bin/build_assets

src/app.yaml : src/app.yaml.dist
	bin/build_app_yaml src/app.yaml.dist src/app.yaml --from-env

deploy : appengine_packages src/ggrc/assets/assets.manifest src/app.yaml

clean_deploy :
	rm -f src/ggrc/assets/stylesheets/dashboard.css
	rm -f src/ggrc/static/dashboard-*.* src/ggrc/assets/assets.manifest
	rm -f src/app.yaml

clean : clean_deploy
