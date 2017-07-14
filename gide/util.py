import json
import subprocess

from urllib.parse import urlparse

import requests


def make_go_get(url):
    """
    """
    return 'go get {0}'.format(urlparse(url).netloc)


def search_packages(key):
    """
    """
    url = 'https://api.github.com/search/repositories'
    headers = {
        'Content-Type': 'application/json',
    }
    params = (
        ('q', '"{0}" language:go'.format(key)),
        ('sort', 'stars'),
        ('order', 'desc'),
    )

    # TODO:
    '''
    github_oauth_token = self.settings.get('github_oauth_token')
    if github_oauth_token:
        curl_args[1:1] = [
            '-u',
            github_oauth_token
        ]
    '''

    return requests.get(url, headers=headers, params=params).json()['items']
