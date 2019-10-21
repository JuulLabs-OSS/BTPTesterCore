#!/usr/bin/env python3
import collections
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


# Build a dict with environment variables beginning with CODE_
def get_code_env():
    PREFIX = 'CODE_'
    code_env = [var for var in list(os.environ.keys()) if var.startswith(PREFIX)]
    values = {var: os.environ[var] for var in code_env}
    return values


# Send all CODE_ environment variables over HTTP; expect JSON back
def send_http_get_json(uri):
    data = json.dumps(get_code_env()).encode()
    req = urllib.request.Request(uri, data, {'Content-Type': 'application/json'})
    response = urllib.request.urlopen(req)
    result = response.read()
    return collections.defaultdict(lambda: None, json.loads(result))


def usage():
    script_name = os.path.basename(sys.argv[0])
    print(("Usage: {} http://server/(path)".format(script_name)))
    sys.exit(1)


if __name__ == '__main__':
    rv = 0  # return value

    url = ""
    if len(sys.argv) > 1:
        url = sys.argv[1]
    if not url.startswith('http'):
        usage()

    # Parse response as JSON and return exit code based on verdict
    try:
        data = send_http_get_json(url)
        print(data)
        for err in data.get('errors', []):
            print("Error: ", err)
        if data['verdict'] == 'fail':
            # Retun failure exit code for Defensics; used with "as instrumentation"
            rv = 1
    except Exception as e:
        print("Response not in expected format (JSON dictionary)")
        print(e)
        rv = 1
    finally:
        sys.exit(rv)
