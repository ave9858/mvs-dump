"""Holds the MVS and CookieExpired classes"""
import json
from base64 import b64decode
from datetime import datetime

import requests


class CookieExpired(ValueError):
    pass


class MVS:
    """Class for talking to the MVS api"""

    def __init__(self, cookie: str):
        self.cookie = cookie
        if not self._cookie_check_expiry():
            raise CookieExpired

        self.mvs_connection = requests.Session()

    def _cookie_check_expiry(self):
        """Check if JWT's expiration date is in the future or not"""
        token = json.loads(b64decode(self.cookie.split(".")[1] + "==="))
        expiration = datetime.fromtimestamp(token["exp"])

        return expiration > datetime.now()

    def get_search(self) -> dict:
        """Return a file link JSON for a given filename"""
        response = self.mvs_connection.post(
            "https://my.visualstudio.com/_apis/AzureSearch/Search?upn=",
            json={"getAllResults": True, "subscriptionLevel": ""},
            headers={
                "User-Agent": "ELinks (textmode)",
                "Accept": "application/json; api-version=1.0",
                "Host": "my.visualstudio.com",
            },
            cookies={"UserAuthentication": self.cookie},
        )
        return response.json()["searchResultsGroupByProduct"]

    def get_products(self, products: list[int]) -> dict:
        """Request a product list JSON from MVS by IDs"""
        response = self.mvs_connection.post(
            "https://my.visualstudio.com/_apis/AzureSearch/GetfilesForListOfProducts?upn=&mkt=",
            json=products,
            headers={
                "User-Agent": "ELinks (textmode)",
                "Accept": "application/json; api-version=1.0",
                "Host": "my.visualstudio.com",
            },
            cookies={"UserAuthentication": self.cookie},
        )
        response.raise_for_status()
        return response.json()["filesForProducts"]
