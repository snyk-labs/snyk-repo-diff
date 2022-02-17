import logging
import urllib.parse
import requests
from typing import Optional, List, Optional, Dict

from retry.api import retry_call
from os import environ
from time import sleep

logger = logging.getLogger(__name__)


class SnykV3Client(object):
    API_URL = "https://api.snyk.io/v3"
    V3_VERS = "2021-08-20~beta"
    USER_AGENT = "pysnyk/snyk_services/sync/diy_scripts"

    def __init__(
        self,
        token: str,
        url: Optional[str] = None,
        version: Optional[str] = None,
        user_agent: Optional[str] = USER_AGENT,
        debug: bool = False,
        tries: int = 1,
        delay: int = 1,
        backoff: int = 2,
    ):
        self.api_token = token
        self.api_url = url or self.API_URL
        self.api_vers = version or self.V3_VERS
        self.api_headers = {
            "Authorization": "token %s" % self.api_token,
            "User-Agent": user_agent,
        }
        self.api_post_headers = self.api_headers
        self.api_post_headers[
            "Content-Type"
        ] = "Content-Type: application/vnd.api+json; charset=utf-8"
        self.tries = tries
        self.backoff = backoff
        self.delay = delay

    def request(
        self,
        method,
        url: str,
        headers: object,
        params: object = None,
        json: object = None,
    ) -> requests.Response:

        resp: requests.Response

        resp = method(
            url,
            json=json,
            params=params,
            headers=headers,
        )

        if resp.status_code == 429:
            logger.debug("RESP: %s" % resp.headers)
            print("Hit 429 Timeout, Sleeping before erroring out")
            sleep(65)
            resp.raise_for_status()
        elif not resp or resp.status_code >= requests.codes.server_error:
            logger.debug("RESP: %s" % resp.headers)
            resp.raise_for_status()

        return resp

    def get(self, path: str, params: dict = {}) -> requests.Response:

        # path = ensure_version(path, self.V3_VERS)
        path = cleanup_path(path)

        if "version" not in params.keys():
            params["version"] = self.V3_VERS

        params = {k: v for (k, v) in params.items() if v}

        # because python bool(True) != javascript bool(True) - True vs true
        for k, v in params.items():
            if isinstance(v, bool):
                params[k] = str(v).lower()

        url = self.api_url + path
        logger.debug("GET: %s" % url)
        # try:
        resp = retry_call(
            self.request,
            fargs=[requests.get, url, self.api_headers, params],
            tries=self.tries,
            delay=self.delay,
            backoff=self.backoff,
            logger=logger,
        )

        logger.debug("RESP: %s" % resp.headers)

        return resp

    def get_all_pages(self, path: str, params: dict = {}) -> List:
        """
        This is a wrapper of .get() that assumes we're going to get paginated results.
        In that case we really just want concated lists from each pages 'data'
        """

        # this is a raw primative but a higher level module might want something that does an
        # arbitrary path + origin=foo + limit=100 url construction instead before being sent here

        limit = params["limit"]

        data = list()

        page = self.get(path, params).json()

        data.extend(page["data"])

        while "next" in page["links"].keys():
            next_url = urllib.parse.urlsplit(page["links"]["next"])
            query = urllib.parse.parse_qs(next_url.query)

            for k, v in query.items():
                params[k] = v

            params["limit"] = limit

            page = self.get(next_url.path, params).json()
            data.extend(page["data"])

        return data


def cleanup_path(path: str):
    if path[0] != "/":
        return f"/{path}"
    else:
        return path


def cleanup_url(path: str):
    if "https://app.snyk.io/api/v1/" in path:
        path = path.replace("https://app.snyk.io/api/v1/", "")

    return path
