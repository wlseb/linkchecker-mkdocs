from __future__ import annotations
import requests
import re
import typing as T
import warnings
import urllib3
import logging
from pathlib import Path
import files

TIMEOUT = 3
RETRYCODES = (400, 404, 405, 503)
# multiple exceptions must be tuples, not lists in general
OKE = requests.exceptions.TooManyRedirects  # FIXME: until full browswer like Arsenic implemented
EXC = (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError)

"""
synchronous routines
"""

def check_urls(
    urls: list[ dict ],
    hdr: dict[str, str] = None,
    verifycert: bool = False
) -> list[tuple[str, str, T.Any]]:

    bads: list[tuple[str, str, T.Any]] = []
    warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
    missing = []

    with requests.Session() as sess:
        if hdr:
            sess.headers.update(hdr)
            sess.max_redirects = 5

        # %% loop
        for u in urls:
            url = u['url']
            logging.debug(f"Checking remote synchronoulsy, path:{u['path']} fn:{u['fn']} url:{u['url']} ...")
            try:
                R = sess.head(url, allow_redirects=True, timeout=TIMEOUT, verify=verifycert)
                if R.status_code in RETRYCODES:
                    if retry(url, hdr, verifycert):
                        logging.info(f"OK RETRY: {url:80s}")
                        continue
                    else:
                        #yield u, url, R.status_code
                        missing.append( [ u['fn'], u['url'], R.status_code ] )
                        logging.info(f"NOT FOUND RETRY: {R.status_code} {url:80s}")
                        continue
            except OKE:
                logging.info(f"OK MANY REDIRECTS: {url:80s}")
                continue
            except EXC as e:
                if retry(url, hdr, verifycert):
                    logging.info(f"OK RETRY EXC: {url:80s}")
                    continue
                missing.append( [ u['fn'], u['url'], str(e) ] )
                #yield u, url, str(e)
                logging.info(f"NOT FOUND EXC: {e} {url:80s}")
                continue

            code = R.status_code
            if code != 200:
                #yield u, url, code
                missing.append( [ u['fn'], u['url'], code ] )
                logging.info(f"NOT FOUND: {R.status_code} {url:80s}")
            else:
                logging.info(f"OK: {url:80s}")

    return missing

def retry(url: str, hdr: dict[str, str] = None, verifycert: bool = False) -> bool:
    ok = False
    try:
        # anti-crawling behavior doesn't like .head() method--.get() is slower but avoids lots of false positives
        R = requests.get(
            url, allow_redirects=True, timeout=TIMEOUT, verify=verifycert, headers=hdr, stream=True
        )
        if R.status_code == 200:
            ok = True
    except EXC:
        pass

    return ok
