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
import requests
import threading
try:
    import simplejson as json
except ImportError:
    import json
#import uuid
#import time

INDEX = 'crawler'

logger = logging.getLogger(__name__)

core = Blueprint('core', __name__)

def crawl_url(url, job_id):
    """ crawl urls using the API /crawl method """
    payload = {'url': url, 'job_id': job_id}
    headers = {'Content-type': 'application/json'}
    method = '/crawl'
    host = 'http://localhost:8000'
    #url = '%s%s' % (g.api_host, method)
    url = '%s%s' % (host, method)
    request = requests.post(url, headers=headers, data=json.dumps(payload))
    print request.request.__dict__
    logger.debug(request.text)
    return request.status_code


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
        'body': {
            'urls': urls,
            'status': {
                'inprogress': {},
                'completed': {},
            }
        },
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
    job_id = data['_id']
    message = "%i URLs added successfully to '%s'!" % (len(urls), job_id)
    logger.debug(message)
    for url in urls:
        ## send POST to /crawler -d '{"job_id": _id, "url": url}'
        thread = threading.Thread(target=crawl_url, args = (url, job_id))
        thread.daemon = True
        thread.start()
    return jsonify(message=message, job_id=data['_id'], success=True), 201


@core.route('/status/<job_id>', methods=['GET'])
def status(job_id):
    """ check the status

    **Example request:**

    .. sourcecode:: http

    GET / HTTP/1.1
    Accept: */*

    **Example response:**

    .. sourcecode:: http

    HTTP/1.1 200 Success
    Content-Type: application/json
    { 'completed': 2, 'inprogress': 2, 'success': True }

    :statuscode 200: success
    :statuscode 404: Not Found
    :statuscode 500: server error
    """
    logger.debug("Checking '%s'", job_id)
    data = {}
    args = {
        'index': INDEX,
        'id': job_id,
        'doc_type': 'queue',
    }
    try:
        data = g.db_client.get(**args)
    except (TransportError, Exception) as error:
        if not getattr(error, 'status_code', None) == 404:
            logger.critical(str(error))
            message = "Something broke... We are looking into it!"
            return jsonify(message=message, success=False), 500
    if not data or not data.get('found', None):
        message = "'%s' Does not exist." % job_id
        logger.warn(message)
        return jsonify(message=message, success=False), 404
    if not data.get('_source', None) \
        or not data['_source'].get('status', None) \
        or not data['_source']['status'].has_key('inprogress') \
        or not data['_source']['status'].has_key('completed'):
            message = "Incorrect data structure: '%s'" % data.keys()
            logger.error(message)
            return jsonify(message=message, success=False), 404
    args = {
        'inprogress': len(data['_source']['status']['inprogress']),
        'completed': len(data['_source']['status']['completed']),
        'success': True
    }
    logger.debug(args)
    return jsonify(**args)


@core.route('/result/<job_id>', methods=['GET'])
def result(job_id):
    """ get the result

    **Example request:**

    .. sourcecode:: http

    GET / HTTP/1.1
    Accept: */*

    **Example response:**

    .. sourcecode:: http

    HTTP/1.1 200 Success
    Content-Type: application/json
    { "urls": ["http://www.abc.com/img/abc.png", "http://www.xyz.com/img/xyz.gif"] }

    :statuscode 200: success
    :statuscode 404: Not Found
    :statuscode 500: server error
    """
    logger.debug("Checking '%s'", job_id)
    data = {}
    args = {
        'index': INDEX,
        'id': job_id,
        'doc_type': 'queue',
    }
    try:
        data = g.db_client.get(**args)
    except (TransportError, Exception) as error:
        if not getattr(error, 'status_code', None) == 404:
            logger.critical(str(error))
            message = "Something broke... We are looking into it!"
            return jsonify(message=message, success=False), 500
    if not data or not data.get('found', None):
        message = "'%s' Does not exist." % job_id
        logger.warn(message)
        return jsonify(message=message, success=False), 404
    if not data.get('_source', None) \
        or not data['_source'].get('status', None) \
        or not data['_source']['status'].has_key('inprogress') \
        or not data['_source']['status'].has_key('completed'):
            message = "Incorrect data structure: '%s'" % data.keys()
            logger.error(message)
            return jsonify(message=message, success=False), 404
    urls = []
    if not data['_source']['status']['completed']:
        message = "'%i' URLs discovered for job_id: '%s'" % (len(urls), job_id)
        logger.debug(message)
        return jsonify(message=message, urls=urls, success=True)
    docs = [{'_id': key} for key in data['_source']['status']['completed']]
    args = {
        'index': INDEX,
        'body': { 'docs': docs },
        'doc_type': 'url',
    }
    try:
        mdata = g.db_client.mget(**args)
    except (TransportError, Exception) as error:
        if not getattr(error, 'status_code', None) == 404:
            logger.critical(str(error))
            message = "Something broke... We are looking into it!"
            return jsonify(message=message, success=False), 500
    if not mdata or not mdata.get('docs', None):
        message = "'%s' Does not exist." % job_id
        logger.warn(message)
        return jsonify(message=message, success=False), 404
    for data in mdata.get('docs'):
        if not data.get('_source', None) \
            or not data['_source'].has_key('image_urls'):
                message = "Incorrect data structure: '%s'" % data.keys()
                logger.error(message)
                return jsonify(message=message, success=False), 404
        urls += data['_source']['image_urls']
    message = "'%i' URLs discovered for job_id: '%s'" % (len(urls), job_id)
    logger.debug(message)
    return jsonify(message=message, urls=urls, success=True)


@core.route('/crawl', methods=['POST'])
def crawl():
    """ crawl the specified URL and update the job_id status

    **Example request:**

    .. sourcecode:: http

    POST / HTTP/1.1
    Accept: application/json
    { 'url': 'http://www.google.com', 'job_id': 'abc', 'force': False }

    **Example response:**

    .. sourcecode:: http

    HTTP/1.1 200 Success
    Content-Type: application/json
    { 'success': True }

    :statuscode 200: success
    :statuscode 404: Not Found
    :statuscode 500: server error
    """
    if not request.json:
        message = "Content-Type: 'application/json' required"
        logger.warn(message)
        return jsonify(message=message, success=False), 400
    if not request.json.get('url', None) \
        or not request.json.get('job_id', None):
        message = "Required: { 'url': 'http://www.google.com', 'job_id': 'abc' }"
        logger.warn(message)
        return jsonify(message=message, success=False), 400
    job_id = request.json['job_id']
    url = request.json['url']
    force = False
    if request.json.get('force', False):
        force = True
    logger.debug("Updating '%s'", job_id)
    data = {}
    args = {
        'index': INDEX,
        'id': job_id,
        'doc_type': 'queue',
    }
    logger.debug(args)
    try:
        data = g.db_client.get(**args)
    except (TransportError, Exception) as error:
        if not getattr(error, 'status_code', None) == 404:
            logger.critical(str(error))
            message = "Something broke... We are looking into it!"
            return jsonify(message=message, success=False), 500
    if not data or not data.get('found', None):
        message = "'%s' Does not exist." % job_id
        logger.warn(message)
        return jsonify(message=message, success=False), 404
    if not data.get('_source', None) \
        or not data['_source'].get('status', None) \
        or not data['_source']['status'].has_key('inprogress') \
        or not data['_source']['status'].has_key('completed'):
            message = "Incorrect data structure: '%s'" % data.keys()
            logger.error(message)
            return jsonify(message=message, success=False), 404
    if not force and data['_source']['status']['completed'].has_key(url):
        message = "'%s' URL already completed!" % url
        logger.info(message)
        return jsonify(message=message, success=True)
    if not force and data['_source']['status']['inprogress'].has_key(url):
        message = "'%s' URL already inprogress!" % url
        logger.info(message)
        return jsonify(message=message, success=True)
    ## updating the parent document with a partial does not override existing keys
    data['_source']['status']['inprogress'][url] = None
    data['_source']['status']['completed'].pop(url, None)
    args = {
        'index': INDEX,
        'id': job_id,
        'body': {
            #'doc': {
                #'status': data['_source']['status']
            #}
            'urls': data['_source']['urls'],
            'status': data['_source']['status']
        },
        'doc_type': 'queue',
    }
    logger.debug(args)
    try:
        result = g.db_client.index(**args)
        #result = g.db_client.update(**args)
    except (TransportError, Exception) as error:
        message = str(error)
        logger.warn(message)
        return jsonify(message=message, success=False), 500
    message = "'%s' URL added successfully to inprogress!" % url
    logger.debug(message)
    crawler = Crawler()
    crawler.main(url)
    args = {
        'index': INDEX,
        'id': url,
        'body': {
            'image_urls': list(crawler.image_urls),
        },
        'doc_type': 'url',
    }
    #logger.debug(args)
    try:
        result = g.db_client.index(**args)
        #result = g.db_client.update(**args)
    except (TransportError, Exception) as error:
        message = str(error)
        logger.warn(message)
        return jsonify(message=message, success=False), 500
    for root_url in crawler.root_urls:
        ## send POST to /crawler -d '{"job_id": _id, "url": url}'
        if root_url not in data['_source']['urls']:
            logger.debug("Adding root_url '%s' to job_id '%s'", root_url,
                job_id)
            data['_source']['urls'][root_url] = None
            thread = threading.Thread(target=crawl_url, args = (root_url,
                job_id))
            thread.daemon = True
            thread.start()
    ## updating the parent document with a partial does not override existing keys
    data['_source']['status']['inprogress'].pop(url, None)
    data['_source']['status']['completed'][url] = None
    args = {
        'index': INDEX,
        'id': job_id,
        'body': {
            #'doc': {
                #'status': data['_source']['status']
            #}
            'urls': data['_source']['urls'],
            'status': data['_source']['status']
        },
        'doc_type': 'queue',
    }
    logger.debug(args)
    try:
        result = g.db_client.index(**args)
        #result = g.db_client.update(**args)
    except (TransportError, Exception) as error:
        message = str(error)
        logger.warn(message)
        return jsonify(message=message, success=False), 500
    message = "'%s' URL added successfully to completed!" % url
    return jsonify(message=message, success=True)
