"""
	crawl the web for images
"""
import sys
import re
import logging
#import os.path
import requests
from requests.exceptions import ConnectionError, TooManyRedirects
from urlparse import urlparse
from bs4 import BeautifulSoup

IMAGE_URL_RE = re.compile(r'\.(img|png|gif)$')
MAX_LEVEL = 2

logger = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)

def get_link_urls(url):
    """ get the hyperlink urls from a url """
    logger.debug("Getting html from '%s'", url)
    try:
        request = requests.get(url)
    except (ConnectionError, TooManyRedirects) as error:
        logger.exception(error)
        return
        yield
    if not request.status_code == 200:
        return
        yield
    soup = BeautifulSoup(request.text, "lxml")
    for ref in soup.findAll(['a', 'img']):
        if ref.has_attr('src'):
            yield ref['src']
        if ref.has_attr('href'):
            yield ref['href']


class Crawler(object):
    """ encapsulate the data as an object """

    def __init__(self):
        """ instantiate the class """
        self.root_urls = set()
        self.absolute_urls = set()
        self.image_urls = set()
        self.image_url_re = IMAGE_URL_RE
        self.max_level = MAX_LEVEL
        self.url = None
        self.root_url = None

    def _set_url(self, url):
        """ set the master or parent url for the class """
        try:
            self.url = urlparse(url)
        except AttributeError as error:
            logger.critical(error)
            raise
        self.root_url = '%s://%s' % (self.url.scheme, self.url.netloc)

    def _parse_urls(self, root_url, level):
        """ parse root_url and recrusively check URLs no more than
            self.max_level
        Args:
            root_url (str): the root url
            level (int): the root_url path level
        """
        logging.debug("parsing root_url, level: '%s', '%s'", root_url, level)
        if level > self.max_level:
            logger.info("All done")
            return
        for link_url in get_link_urls(root_url):
            try:
                url = urlparse(link_url)
            except AttributeError as error:
                logger.warn(error)
                continue
            if url.scheme == 'javascript':
                continue
            root_link_url = '%s://%s' % (url.scheme, url.netloc)
            ## Parse all URLs encountered and add them to the queue, only if
            ## you are on the first level of crawling (root URLs or absolute
            ## URLs?)
            if level == 0 and url.scheme and url.netloc:
                logger.debug(url)
                self.root_urls.add(root_link_url)
                ## send new URL to API endpoint with UUID
            if not url.path or url.path == '/' or re.search(r'%', url.path):
                logger.warn("url.path not valid: '%s'", url)
                continue
            if not url.netloc or root_link_url == self.root_url:
                ## need to determine how to handle non-root relative paths
                if not re.match(r'/', url.path) or re.match(r'../', url.path):
                    #path = re.sub('/?\.\.', '', path)'
                    continue
                shift = self.max_level + 1
                ## only crawl for path levels <= shift. Need to iterate over
                ## each path <= shift to include any sub paths
                path_parts = url.path.split('/')
                if len(path_parts) > shift:
                    path = '/'.join(path_parts[:shift]) + '/'
                else:
                    path = url.path
                pos_url = self.root_url + path
                if re.search(self.image_url_re, pos_url):
                    self.image_urls.add(pos_url)
                    continue
                if len(path_parts) > shift and re.search(self.image_url_re,
                    path_parts[shift]):
                    self.image_urls.add(pos_url + path_parts[shift])
                    continue
                if pos_url not in self.absolute_urls:
                    self.absolute_urls.add(pos_url)
                    self._parse_urls(pos_url,
                        len(path.rstrip('/').split('/')) - 1)

    def main(self, url):
        """ run the main logic """
        logger.info("Starting")
        logger.debug(url)
        if not self.root_url:
            self._set_url(url)
        ## only parse root_urls for now
        self._parse_urls(self.root_url, 0)
        logger.debug("%i : '%s'", len(self.root_urls), self.root_urls)
        logger.debug("%i : '%s'", len(self.image_urls), self.image_urls)
        logger.info("Finished")

    def test(self):
        """ test """
        pass


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=("%(asctime)s %(levelname)s %(name)s[%(process)s] : %(funcName)s"
            " : %(message)s"),
    )
    if len(sys.argv) != 2:
        print "Argument required!"
        sys.exit(1)
    Crawler().main(sys.argv[1])
