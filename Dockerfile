FROM brandond/obra-upgrade-calculator AS builder
USER root
RUN apk --no-cache upgrade
RUN apk --no-cache add alpine-sdk python3-dev

ENV HOME=/root
COPY app/requirements.txt /app/requirements.txt
RUN /app/venv/bin/pip install -r /app/requirements.txt


FROM brandond/obra-upgrade-calculator AS minifier
USER root
RUN apk --no-cache upgrade

RUN /app/venv/bin/pip install css-html-js-minify flake8
COPY ./app/ ./.flake8 /tmp/flake8/app/
RUN /app/venv/bin/flake8 /tmp/flake8/app
COPY ./static/ /app/static/
RUN /app/venv/bin/css-html-js-minify --comments --overwrite /app/static/


FROM brandond/obra-upgrade-calculator
USER root
RUN apk --no-cache upgrade

LABEL maintainer="Brad Davidson <brad@oatmail.org>"
RUN apk --no-cache add bash libstdc++ openssl uwsgi-http uwsgi-python3 uwsgi-router_static
COPY --chown=guest:users --from=builder /app/venv/ /app/venv/
RUN test ! -e /tmp && \
    mkdir /tmp && \
    chmod 1777 /tmp || \
    true

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]

USER guest
VOLUME ["/tmp"]
EXPOSE 8080 8443
CMD ["uwsgi", "--yaml", "/app/conf/uwsgi.yaml"]
ENV UWSGI_CERT=/tmp/server.pem UWSGI_KEY=/tmp/server.key CACHE_TYPE=uwsgi

COPY --chown=guest:users ./app/ /app/
COPY --chown=guest:users ./conf/ /app/conf/
COPY --chown=guest:users --from=minifier /app/static/ /app/static/
