from flask import Flask, request
from flask_restplus import Resource, fields, marshal
import logging

logger = logging.getLogger(__name__)


def register(api, cache):
    # TODO - how am I going to store PushSubscription data now that there's no subscriptionId?
    # Now need some way to store it as part of session data or something, but I don't want
    # to require registration...
    ns = api.namespace('notifications', 'Push Notifications')
