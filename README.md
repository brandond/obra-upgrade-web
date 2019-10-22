OBRA Upgrade Web
=======================

A basic web interface for data scraped by obra-upgrade-calculator.

The backend is built on Flask-RESTPlus in UWSGI. It can be run behind Nginx with `http2_push_preload` enabled for HTTP/2 Server Push support.

The frontend is based on simple HTML, Knockout.js for templating, and page.js for navigation.
