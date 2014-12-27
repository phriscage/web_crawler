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
#import uuid

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

    HTTP/1.1 201 Created
    Content-Type: application/json
    job_id: 'asdfasdfasdf'

    :statuscode 201: created
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
    ## use ES auto id for now
    #_id = str(uuid.uuid4())
    ## I need O(1) lookups for each URL as well as uniqueness
    #urls = set(request.json['urls'])
    urls = dict((str(key),None) for key in request.json['urls'])
    args = {
        'index': INDEX,
        'body': { 'urls': urls, 'incoming': {}, 'completed': {} },
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
    message = "%i URLs added successfully to '%s'!" % (len(urls.keys()),
        data['_id'])
    logger.debug(message)
    #for url in urls:
        ## send POST to /crawler -d '{"job_id": _id, "url": url}'
    return jsonify(message=message, job_id=data['_id'], success=True), 201

@core.route('/status/<job_id>', methods=['GET'])
def status(job_id):
    """ check the status

    **Example request:**

    .. sourcecode:: http

    POST / HTTP/1.1
    Accept: application/json

    **Example response:**

    .. sourcecode:: http

    HTTP/1.1 201 Created
    Content-Type: application/json
    { 'completed': 2, 'inprogress': 2, 'success': True }

    :statuscode 200: success
    :statuscode 404: Not Found
    :statuscode 500: server error
    """
    logger.debug("Checking '%s'", job_id)
    data = {}
    try:
        data = g.db_client.get(INDEX, job_id)
    except (TransportError, Exception) as error:
        if not getattr(error, 'status_code', None) == 404:
            logger.critical(str(error))
            message = "Something broke... We are looking into it!"
            return jsonify(message=message, success=False), 500
    if data.get('found', None) and data.get('_source', None):
        if not data['_source'].has_key('incoming') \
            or not data['_source'].has_key('completed'):
                message = "Incorrect data structure: '%s'" % data['_source'].keys()
                logger.error(message)
                return jsonify(message=message, success=False), 404
        result = {
            'incoming': len(data['_source']['incoming'].keys()),
            'completed': len(data['_source']['completed'].keys()),
            'success': True
        }
        logger.debug(result)
        return jsonify(**result)
    message = "'%s' Does not exist." % job_id
    logger.warn(message)
    return jsonify(message=message, success=False), 404
