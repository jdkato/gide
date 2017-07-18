from util import (
    search_packages,
    make_go_get
)

def search(key):
    """
    """
    packages = search_packages(key)
    for package in packages:
        print(make_go_get(package['html_url']))
