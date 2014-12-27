"""
    views file contains all the routes for the app and maps them to a
    specific hanlders function.
"""
import os
import sys
import logging
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) +
                '/../../../../lib')
from crawler.lib.crawler import Crawler
from flask import Blueprint, jsonify, request, g
from elasticsearch import TransportError
import uuid

INDEX = 'crawler'

logger = logging.getLogger(__name__)

core = Blueprint('core', __name__)

@core.route('/', methods=['POST'])
def create():
    """ create a queue

    **Example request:**

    .. sourcecode:: http

    POST / HTTP/1.1
    Accept: application/json
    { 'urls': ['http://www.google.com', 'http://www.cnn.com', ...] }

    **Example response:**

    .. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/json
    job_id: 'asdfasdfasdf'

    :statuscode 200: success
    :statuscode 400: bad data
    :statuscode 500: server error
    """

    if not request.json:
        message = "Content-Type: 'application/json' required"
        logger.warn(message)
        return jsonify(message=message, success=False), 400
    if not request.json.get('urls', None) \
        or not type(request.json['urls']) == list:
        message = "Required: { 'urls': ['http://www.google.com', 'http://www.cnn.com', ...] }"
        logger.warn(message)
        return jsonify(message=message, success=False), 400
    _id = str(uuid.uuid4())
    urls = set(request.json['urls'])
    args = {
        'index': INDEX,
        'id': _id,
        'body': { 'urls': urls },
        'doc_type': 'queue'
    }
    logger.debug(args)
    data = {}
    try:
        data = g.db_client.index(**args)
    except (TransportError, Exception) as error:
        message = str(error)
        logger.warn(message)
        return jsonify(message=message, success=False), 500
    message = "%i URLs added successfully to '%s'!" % (len(urls), _id)
    logger.debug(message)
    #for url in urls:
        ## send POST to /crawler -d '{"job_id": _id, "url": url}'
    return jsonify(message=message, job_id=_id, success=True), 200
