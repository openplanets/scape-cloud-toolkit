# -*- coding: utf-8 -*-
"""
Copyright 2014 Universitatea de Vest din Timișoara

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

@author: Marian Neagul <marian@info.uvt.ro>
@contact: marian@info.uvt.ro
@copyright: 2014 Universitatea de Vest din Timișoara
"""

import hmac
import urllib2
import hashlib
import urlparse
import logging


class SkapurClient(object):
    """
    For now this poorly written. It should be redesigned
    """

    def __init__(self, url, secret, prefix=None):
        self.url = urlparse.urljoin(url, "/skapur/v1/")
        self.secret = secret
        parsed_url = urlparse.urlparse(url)
        if parsed_url.path and not parsed_url.path == "/":
            raise AttributeError("Can't handle URL paths")

    def store(self, path, content):
        log = logging.getLogger("skapur.store")
        urllib2.build_opener(urllib2.HTTPHandler)
        if path.startswith("/"):
            log.debug("Stripping / from requested url")
            path = path[1:]
        token = hmac.new(self.secret, "/" + path, hashlib.sha256).hexdigest()
        path = "%s/%s" % (token, path)
        request_path = urlparse.urljoin(self.url, path)
        log.debug("Storing to: %s", request_path)
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(request_path, data=content)
        request.add_header('Content-Type', 'application/octet-stream')
        request.get_method = lambda: 'PUT'
        url = opener.open(request)

    def get(self, path):
        log = logging.getLogger("skapur.get")
        if path.startswith("/"):
            path = path[1:]
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        path = "-/%s" % path
        request_path = urlparse.urljoin(self.url, path)
        request = urllib2.Request(request_path)
        log.debug("Retrieving from %s", request_path)
        url = opener.open(request)
        return url.read()


if __name__ == "__main__":
    client = SkapurClient(secret="5fc0a568352e4213a5dfefb1f79fab6b",
                          url="http://euca-194-102-62-138.euca3.cloud.ieat.ro:8088/")
    text = "Merge"
    path = "/test/test.txt"
    client.store(path, text)
    new_text = client.get(path)
    assert new_text == text
