#!/usr/bin/env python

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import url_contains

from secret import get_secret


def get_token(email: str, passwd: str) -> str:

    opts = Options()
    opts.add_argument('--headless')

    drv = Chrome(options=opts)
    drv.implicitly_wait(5)

    drv.get('https://my.visualstudio.com/')

    # Fill in email
    email_field = drv.find_element(By.ID, 'i0116')
    email_field.send_keys(email + '\n')

    # Fill in password
    WebDriverWait(drv, 5).until(url_contains('https://login.live.com/'))
    passwd_field = drv.find_element(By.ID, 'i0118')
    passwd_field.send_keys(passwd + '\n')

    # "Stay signed in?"..
    drv.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()

    # Get cookie..
    WebDriverWait(drv, 5).until(url_contains('https://my.visualstudio.com/'))
    token: str = drv.get_cookie('UserAuthentication')['value']

    drv.close()
    return token


def main():

    with open('mvs.cookie', 'w') as cookie:
        cookie.write(get_token(get_secret('email'), get_secret('password')))


if __name__ == '__main__':
    main()
