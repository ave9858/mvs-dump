import requests
from base64 import b64decode
from datetime import datetime
import json

class MVS:

    # More-or-less private interface

    def _cookie_check_expiry(self):
        """Check if JWT's expiration date is in the future or not"""
        try:
            token = json.loads(b64decode(self.cookie.split('.')[1] + '==='))
            expiration = datetime.fromtimestamp(token['exp'])
            
            if expiration > datetime.now():
                return True
            return False
        except:
            return False

    def _process_cookie(self, cookie: str) -> bool:
        self.cookie = cookie
        if not self._cookie_check_expiry():
            raise Exception('cookie invalid')
        # TODO initialize user data from other parts of the cookie.

    def _ensure_cookie_validity(f):
        # Excuse this retardation, 'args[0]' is simply 'self'
        def checked(*args, **kwargs):
            if args[0]._cookie_check_expiry():
                return f(*args, **kwargs)
            else:
                raise Exception('Cookie expired')
        return checked

    @_ensure_cookie_validity
    def _get_products(self, products: list[int]) -> requests.Response:
        """Request a product list JSON from MVS by IDs"""
        REQUEST_URL = 'https://my.visualstudio.com/_apis/AzureSearch/GetfilesForListOfProducts?upn=&mkt='
        
        response = self.mvs_connection.post(
            REQUEST_URL,
            json = products,
            headers = {
                'User-Agent': 'ELinks (textmode)',
                'Accept': 'application/json; api-version=1.0',
                'Host': 'my.visualstudio.com'
            },
            cookies = {
                'UserAuthentication': self.cookie
            }
        )
        if response.status_code != 200:
            raise Exception(f'Error response {response.status_code}')
        return response
    
    @_ensure_cookie_validity
    def _get_link(self, filename: str) -> requests.Response:
        """Return a file link JSON for a given filename"""
        REQUEST_URL = 'https://my.visualstudio.com/_apis/Download/GetLink'

        response = self.mvs_connection.get(
            REQUEST_URL,
            params = {
                'friendlyFileName': filename,
                'upn': '',
                'productId': 8228 # Visual Studio Community 2022 (version 17.1)
            },
            cookies = {
                'UserAuthentication': self.cookie
            }
        )
        if response.status_code != 200:
            raise Exception(f'Error response {response.status_code}')
        return response

    # "Public" interface

    def get_products(self, products: list[int]) -> dict:
        return json.loads(self._get_products(products).text)['filesForProducts']

    def get_link(self, filename: str) -> str:
        return json.loads(self._get_link(filename).text)['url']

    def __init__(self, cookie: str):
        self._process_cookie(cookie)
        self.mvs_connection = requests.Session()