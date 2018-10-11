#!/usr/bin/env bash
# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

set -o nounset
set -o errexit

project_name () {
  # Get proper project name
  # args:
  #  -p: if set the project name will be the name of the repo parent folder.
  #  -d: default project name, if parent folder is not set or valid.
  # returns: project name containing only alphanumeric characters

  # parse the command line options
  while [[ "$#" -gt 0 ]]
  do
    OPT_NAME="$1"

    case $OPT_NAME in
      -p|--parent)
        RESULT=$( cd "$(dirname "$0")/../.." ; echo ${PWD##*/}  )
      ;;
      -d|--default)
        DEFAULT="$2"
        shift  # extra shift for the current options's value
      ;;
      *)  # an unknown option found
      ;;
    esac
    shift  # drop the just-processed option/argument
  done
  if [[ -n "${RESULT:-}" ]]; then
    echo "${RESULT:-}" | sed 's/[^A-Za-z0-9]//g'
  else
    echo "${DEFAULT:-}" | sed 's/[^A-Za-z0-9]//g'
  fi
}

setup () {
  if [ -z "${1:-}" ]; then
    echo "Missing mandatory project parameter"
    exit 1
  else
    PROJECT="${1}"
  fi

  SERVICE=$2

  docker-compose --file ${DOCKER_COMPOSE_FILE} \
    --project-name ${PROJECT} \
    up --build --force-recreate -d ${SERVICE}
}

teardown () {
  if [ -z "${1:-}" ]; then
    echo "Missing mandatory project parameter"
    exit 1
  else
    PROJECT="${1}"
  fi

  docker-compose --file ${DOCKER_COMPOSE_FILE} -p ${PROJECT} stop
}

print_line () {
echo "
###############################################################################
"
}

provision_dev() {
  local dev_server=$1
  echo "Provisioning ${PROJECT}_$dev_server"
  docker exec -i ${PROJECT}_${dev_server} su -c "
    source /vagrant/bin/init_vagrant_env
    ln -s /vagrant-dev/node_modules /vagrant/node_modules
    build_assets
    make appengine_packages
  "
}


provision_dev_for_selenium() {
  local dev_server=$1
  docker exec -i ${PROJECT}_${dev_server} bash -c "
    source /vagrant/bin/init_vagrant_env
    source /vagrant/bin/init_test_env
    ln -s /vagrant-dev/node_modules /vagrant/node_modules
    echo ""Set env vars and rebuild asset files for $dev_server""
    deploy_appengine extras/deploy_settings_local.sh \
      extras/deploy_settings_selenium.override.sh
    echo ""Resetting the DB for $dev_server""
    db_reset -d ggrcdevtest
  "
  echo "Running dev server $dev_server"
  docker exec -id ${PROJECT}_${dev_server} bash -c "
    source /vagrant/bin/init_vagrant_env
    launch_gae_ggrc &> test/selenium/logs/${dev_server}.txt
  "
}


setup_for_selenium () {
  mkdir -p test/selenium/logs
  rm -rf test/selenium/logs/*

  for dev_server in cleandev_1 cleandev_destructive_1; do
    provision_dev_for_selenium $dev_server &
  done
  wait
}


integration_acl_tests () {
  PROJECT=$1
  print_line

  provision_dev "cleandev_1"

  echo "Running ${PROJECT}"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    /vagrant/bin/run_integration_acl
  " && rc=$? || rc=$?

  print_line
  return $rc
}


integration_ggrc_tests () {
  PROJECT=$1
  print_line

  provision_dev "cleandev_1"

  echo "Running ${PROJECT}"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    /vagrant/bin/run_integration_ggrc
  " && rc=$? || rc=$?

  print_line
  return $rc
}


integration_non_ggrc_tests () {
  PROJECT=$1
  print_line

  provision_dev "cleandev_1"

  echo "Running ${PROJECT}"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    /vagrant/bin/run_integration_non_ggrc
  " && rc=$? || rc=$?

  print_line
  return $rc
}


integration_tests () {
  PROJECT=$1
  print_line

  provision_dev "cleandev_1"

  echo "Running ${PROJECT}"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    /vagrant/bin/run_integration
  " && rc=$? || rc=$?

  print_line
  return $rc
}


selenium_tests () {
  PROJECT=$1
  print_line

  echo "Running Selenium tests"
  docker exec -i ${PROJECT}_selenium_1 sh -c "
    python /selenium/run_selenium.py" && rc=$? || rc=$?

  mv ./test/selenium/logs/results.xml ./test/selenium.xml || true

  print_line
  return $rc
}


unittests_tests () {
  PROJECT=$1
  print_line

  provision_dev "cleandev_1"

  echo "Running python unit tests"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    /vagrant/bin/run_unit
  " && unit_rc=$? || unit_rc=$?

  [[ unit_rc -eq 0 ]] && echo "PASS" || echo "FAIL"

  print_line

  echo "Running karma tests"

  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    /vagrant/node_modules/karma/bin/karma start \\
      /vagrant/karma.conf.js --single-run --reporters dots,junit
  " && karma_rc=$? || karma_rc=$?

  [[ karma_rc -eq 0 ]] && echo "PASS" || echo "FAIL"

  print_line
  return $((unit_rc * unit_rc + karma_rc * karma_rc))
}


code_style_tests () {
  PROJECT=$1
  print_line

  echo "Running pylint"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    /vagrant/bin/check_pylint_diff
  " && pylint_rc=$? || pylint_rc=$?

  if [[ pylint_rc -eq 0 ]]; then
    echo "PASS"
    pylint_error=''
  else
    echo "FAIL"
    pylint_error='<error type="pylint" message="Pylint error"></error>'
  fi

  print_line

  echo "Running flake8"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    cd /vagrant
    flake8 .
  " && flake_rc=$? || flake_rc=$?

  if [[ flake_rc -eq 0 ]]; then
    echo "PASS"
    flake8_error=''
  else
    echo "FAIL"
    flake8_error='<error type="flake8" message="Flake8 error"></error>'
  fi

  print_line

  echo "Running eslint"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    export PATH=\$PATH:/vagrant-dev/node_modules/.bin
    /vagrant/bin/check_eslint_diff
  " && eslint_rc=$? || eslint_rc=$?

  if [[ eslint_rc -eq 0 ]]; then
    echo "PASS"
    eslint_error=''
  else
    echo "FAIL"
    eslint_error='<error type="eslint" message="ESLint error"></error>'
  fi

  print_line

  echo "Running misspell"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    make misspell
  " && misspell_rc=$? || misspell_rc=$?

  if [[ misspell_rc -eq 0 ]]; then
    echo "PASS"
    misspell_error=''
  else
    echo "FAIL"
    misspell_error='<error type="misspell" message="Misspell error"></error>'
  fi

  print_line

  echo "Running license header check"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    /vagrant/bin/check_license_headers
  " && license_rc=$? || license_rc=$?

  if [[ license_rc -eq 0 ]]; then
    echo "PASS"
    license_error=''
  else
    echo "FAIL"
    license_error='<error type="misspell" message="Misspell error"></error>'
  fi

  print_line

  echo '<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="code-style" tests="3" errors="'$((pylint_rc + flake_rc))'" failures="0" skip="0">
  <testcase classname="pylint.pylint" name="pylint" time="0">'$pylint_error'</testcase>
  <testcase classname="flake8.flake8" name="flake8" time="0">'$flake8_error'</testcase>
  <testcase classname="eslint.eslint" name="eslint" time="0">'$eslint_error'</testcase>
  <testcase classname="misspell.misspell" name="misspell" time="0">'$misspell_error'</testcase>
  <testcase classname="license.license" name="license" time="0">'$license_error'</testcase>
</testsuite>' > test/lint.xml

  print_line
  return $((pylint_rc * pylint_rc + flake_rc * flake_rc + eslint_rc * eslint_rc + misspell_rc * misspell_rc + license_rc * license_rc))
}


checkstyle_tests () {
  PROJECT=$1
  print_line

  echo "Running pylint"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    pylint -f parseable src/ggrc\
                        src/ggrc_basic_permissions\
                        src/ggrc_gdrive_integration\
                        src/ggrc_workflows\
                        test/integration\
                        test/selenium/src\
                        test/unit\
                        > test/pylint.out
  " || true

  print_line

  echo "Running eslint"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    eslint -f checkstyle src -o test/eslint.xml
  " || true

  print_line

  echo "Running flake8"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    flake8 --config setup.cfg src/ test/ > test/flake8.out
  " || true

  print_line

  echo "Running misspell"
  docker exec -i ${PROJECT}_cleandev_1 su -c "
    source /vagrant/bin/init_vagrant_env
    make misspell
  " || true

  print_line
}
