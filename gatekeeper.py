import asyncio
import json
import os
import threading
import time

import kubernetes
from flask import Flask, redirect, request
from requests_oauthlib import OAuth2Session

kubernetes.config.load_kube_config()

ingresses = {}

gatekeeper_is_https = os.environ.get('GATEKEEPER_IS_HTTPS', 'false').lower() in ['1', 'true']
gatekeeper_host = os.environ['GATEKEEPER_HOST']

client_id = os.environ['OAUTH_CLIENT_ID']
client_secret = os.environ['OAUTH_CLIENT_SECRET']

authorization_base_url = os.environ.get('OAUTH_AUTHORIZATION_BASE_URL', 'https://accounts.google.com/o/oauth2/v2/auth')
token_url = os.environ.get('OAUTH_TOKEN_URL', 'https://accounts.google.com/o/oauth2/v4/token')

redirect_uri = '{}://{}/callback'.format('https' if gatekeeper_is_https else 'http', gatekeeper_host)

app = Flask(__name__)


def watch_ingresses():
    v1beta1_api = kubernetes.client.ExtensionsV1beta1Api()
    watch = kubernetes.watch.Watch()

    for e in watch.stream(v1beta1_api.list_ingress_for_all_namespaces):
        ingress = e['object']
        print(e)
        for rule in ingress.spec.rules:
            for path in rule.http.paths:
                event_type = e.get('type', 'ADDED')
                if event_type == 'ADDED':
                    ingresses[rule.host] = ingresses.get(rule.host, {})
                    ingresses[rule.host][path.path or '/'] = ingress.metadata.labels
                elif event_type == 'DELETED':
                    print('del')
                    if rule.host in ingresses:
                        del ingresses[rule.host][path.path or '/']
                        if not ingresses[rule.host]:
                            del ingresses[rule.host]


@app.route('/auth')
def auth():
    sess = OAuth2Session(client_id, scope=['https://www.googleapis.com/auth/userinfo.email'], redirect_uri=redirect_uri)
    authorization_url, state = sess.authorization_url(authorization_base_url, access_type='offline', propmt='select_account')

    return redirect(authorization_url, code=302)


@app.route('/callback')
def callback():
    sess = OAuth2Session(client_id, scope=['https://www.googleapis.com/auth/userinfo.email'], redirect_uri=redirect_uri)
    sess.fetch_token(token_url, client_secret=client_secret, authorization_response=request.url_root)

    print(sess.get('https://www.googleapis.com/oauth2/v1/userinfo'))


@app.route('/healthz')
def healthz():
    return ''


t1 = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080})
t1.start()
t2 = threading.Thread(target=watch_ingresses)
t2.start()
