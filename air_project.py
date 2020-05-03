import json
import os

import flask
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import nltk
import requests

from external_methods import load_files, \
    search

nltk.download('punkt')
nltk.download("stopwords")

from flask import url_for

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_id.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/drive']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'

app = flask.Flask(__name__)
# Note: A secret key is included in the sample so that it works.
# If you use this code in your application, replace this with a truly secret
# key. See https://flask.palletsprojects.com/quickstart/#sessions.
app.secret_key = os.environ["gapp_secret"]

app.config['JSON_AS_ASCII'] = False


@app.route('/')
def index():
    return flask.render_template("index.html")


@app.route("/search")
def search_page():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    return flask.render_template("search_form.html")


@app.route("/api_search")
def api_search():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    # drive = googleapiclient.discovery.build(
    #     API_SERVICE_NAME, API_VERSION, credentials=credentials)
    query = flask.request.args.get('query')
    lst = search(query, credentials.client_id)
    return flask.jsonify(lst)


@app.route("/duplicates")
def duplicates():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    test_dir = 'index_files'
    with open(test_dir + '/' + 'dupls' + credentials.client_id) as json_file:
        dupls = json.load(json_file)
    flask.session['credentials'] = credentials_to_dict(credentials)
    return flask.render_template('duplicateslist.html', lst=dupls)


@app.route('/delete_indices')
def delete_indices():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    test_dir = 'index_files'
    if os.path.exists(test_dir + '/' + 'index' + credentials.client_id):
        os.remove(test_dir + '/' + 'index' + credentials.client_id)
    if os.path.exists(test_dir + '/' + 'dupls' + credentials.client_id):
        os.remove(test_dir + '/' + 'dupls' + credentials.client_id)
    return flask.redirect(url_for('index'))


@app.route('/load')
def load():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    return flask.render_template('load_menu.html')


@app.route('/load_dupls')
def load_dupls():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    status = load_files(drive, credentials.client_id, ['duplicates'])
    if status['duplicates'] == 1:
        return flask.redirect(url_for('index'))
    else:
        return flask.render_template('nothing_to_show.html')


@app.route('/load_search')
def load_search():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    status = load_files(drive, credentials.client_id, ['index'])
    if status['inverted_index'] == 1:
        return flask.redirect(url_for('index'))
    else:
        return flask.render_template('nothing_to_show.html')


@app.route('/load_both')
def load_both():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    drive = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    status = load_files(drive, credentials.client_id, ['duplicates', 'index'])
    return flask.redirect(url_for('index'))

@app.route("/remove", methods=['POST'])
def delete_file():
    data = json.loads(flask.request.data)
    # data = json.loads(flask.get_json(force=True))
    file_id = data['file_id']
    credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
    drive = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    try:
        drive.files().delete(fileId=file_id).execute()
        status = 0
    except Exception as e:
        print(e)
        status = -1
    return flask.jsonify(status=status)


@app.route('/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    flask.session['state'] = state

    return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)
    return flask.redirect(flask.url_for('index'))


@app.route('/revoke')
def revoke():
    if 'credentials' not in flask.session:
        return ('You need to <a href="/authorize">authorize</a> before ' +
                'testing the code to revoke credentials.')

    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

    revoke = requests.post('https://oauth2.googleapis.com/revoke',
                           params={'token': credentials.token},
                           headers={'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        return ('Credentials successfully revoked.' + index())
    else:
        return ('An error occurred.' + index())


@app.route('/clear')
def clear_credentials():
    if 'credentials' in flask.session:
        del flask.session['credentials']
    return ('Credentials have been cleared.<br><br>' +
            index())


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}



@app.context_processor
def utility_processor():
    test_dir = 'index_files'

    def dupls_exist():
        if 'credentials' in flask.session:
            client_id = flask.session['credentials']['client_id']
            return os.path.exists(test_dir + '/' + 'dupls' + client_id)
        return False

    def index_exist():
        if 'credentials' in flask.session:
            client_id = flask.session['credentials']['client_id']
            return os.path.exists(test_dir + '/' + 'index' + client_id)
        return False

    return dict(dupls_exist=dupls_exist, index_exist=index_exist, user_loged_in='credentials' in flask.session)


if __name__ == '__main__':
    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Specify a hostname and port that are set as a valid redirect URI
    # for your API project in the Google API Console.
    app.run('0.0.0.0', 8080, debug=True)
    # app.run('localhost', 8080, debug=True)
    # app.run('127.0.0.1', 8080, debug=True)
