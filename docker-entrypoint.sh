#!/bin/bash
set -eo pipefail
shopt -s nullglob

if [ -f ${UWSGI_KEY} -a -f ${UWSGI_CERT} ] ; then
  echo "Skipping cert generation"
else
  umask 77
  openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -keyout ${UWSGI_KEY} -out ${UWSGI_CERT} -subj "/O=container/OU=uwsgi/CN=$HOSTNAME"
fi

exec "$@"
