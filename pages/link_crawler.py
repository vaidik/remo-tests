#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import requests
import threading
from bs4 import BeautifulSoup
from unittestzero import Assert

from pages.page import Page


class LinkCrawler(Page):

    def collect_links(self, url, relative=True, name=True, **kwargs):
        """Collects links for given page URL.

        If name is True, then links will be collected for whole page.
        Use name argument to pass tag name of element.
        Use kwargs to pass id of element or its class name.
        Because 'class' is a reserved keyword in Python,
        you need to pass class as: **{'class': 'container row'}.

        Read more about searching elements with BeautifulSoup.
        See: http://goo.gl/85BuZ
        """

        #support for relative URLs
        if relative:
            url = '%s%s' % (self.base_url, url)

        #get the page and verify status code is OK
        r = requests.get(url)
        Assert.true(
            r.status_code == requests.codes.ok,
            u'{0.url} returned: {0.status_code} {0.reason}'.format(r))

        #collect links
        parsed_html = BeautifulSoup(r.text)
        urls = [anchor['href'] for anchor in
                parsed_html.find(name, attrs=kwargs).findAll('a')]

        #prepend base_url to relative links
        return map(
            lambda u: u if u.startswith('http') else '%s%s' % (self.base_url, u), urls)

    def verify_status_code_is_ok(self, url):
        if not self.should_verify_url(url):
            return True
        requests.adapters.DEFAULT_RETRIES = 5
        try:
            r = requests.get(url, verify=False, allow_redirects=True)
        except requests.Timeout:
            r.status_code = 408

        if not r.status_code == requests.codes.ok:
            return u'{0.url} returned: {0.status_code} {0.reason}'.format(r)
        else:
            return True

    def should_verify_url(self, url):
        """Return false if the url does not need to be verified."""
        bad_urls = ['%s/' % self.base_url, '%s#' % self.base_url]
        return not (url.startswith('%sjavascript' % self.base_url) or
                    url.startswith('%sftp://' % self.base_url) or
                    url.startswith('%sirc://' % self.base_url) or
                    url in bad_urls)


    def verify_status_codes_are_ok(self, urls):
        ''' should use a queue to limit concurrency '''
        results = []
        ''' remove duplicates '''
        urls = list(set(urls));
        def task_wrapper(url):
            checkresult = self.verify_status_code_is_ok(url)
            if checkresult is not True:
                results.append(checkresult)

        threads = [threading.Thread(target=task_wrapper, args=(url,)) for url in urls]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return (len(results) == 0, results)
