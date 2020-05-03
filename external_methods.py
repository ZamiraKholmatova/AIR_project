import hashlib
import io
import json
import os
import shutil
from collections import Counter

import chardet
import nltk
import textract
from googleapiclient.http import MediaIoBaseDownload
from nltk.corpus import stopwords

from norvig_spellcheker import fix_typo_norvig


def chunk_reader(fobj, chunk_size=1024):
    while True:
        chunk = fobj.read(chunk_size)
        if not chunk:
            return
        yield chunk


def check_for_duplicates(path, client_id, files, origs, hash=hashlib.sha1):
    hashes = {}
    dupls = []
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            hashobj = hash()
            for chunk in chunk_reader(open(full_path, 'rb')):
                hashobj.update(chunk)
            file_id = (hashobj.digest(), os.path.getsize(full_path))
            duplicate = hashes.get(file_id, None)
            if duplicate:
                hashes[file_id].append(filename)
            else:
                hashes[file_id] = [filename]
    if len(hashes) == 0:
        return None
    else:
        k = 0
        for el in hashes:
            temp = []
            if len(hashes[el]) > 1:
                k += 1
                s = -1
                for f in hashes[el]:
                    s += 1
                    for ids in files:
                        if files[ids][0] == f:
                            temp.append(
                                {'id': ids,
                                 'name': origs[ids][0],
                                 'name_on_disk': f,
                                 'modified_time': origs[ids][1],
                                 'url': origs[ids][2],
                                 'number': '{}.{}'.format(k, s)})
                dupls.append(temp)
    with open('index_files' + '/' + 'dupls' + client_id, "w") as json_file:
        json.dump(dupls, json_file)
    return 1


def list_files(service):
    def get_page(page_token):
        return service.files().list(q="mimeType != 'application/vnd.google-apps.folder'",
                                    pageSize=1000, pageToken=page_token,
                                    fields="nextPageToken,files(id,name, modifiedTime, owners, mimeType, webViewLink)").execute()

    page_token = ''
    files = []
    while page_token is not None:
        results = get_page(page_token)
        page_token = results.get('nextPageToken')
        files = files + results.get('files', [])
    files_dict = dict()
    file_names = dict()
    orig_names = dict()
    for file_ in files:
        if file_.get('name').split('.')[-1] in ['docx', 'txt']:
            if file_.get('owners')[0]['me']:
                filename = file_.get('name').replace(' ', '')
                if filename in file_names:
                    file_names[filename] += 1
                    k = file_names[filename]
                    name = str(k) + filename
                else:
                    name = filename
                    file_names[name] = 1
                files_dict[file_.get('id')] = (name, file_.get('modifiedTime'), file_.get('webViewLink'))
                orig_names[file_.get('id')] = (file_.get('name'), file_.get('modifiedTime'), file_.get('webViewLink'))
    return files_dict, orig_names


def gdrive_download_file(drive_service, file_id, file_name, path_to_save):
    # downloads file and saves it under the path
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        # print("Download %s, %d%%." % (file[1], int(status.progress() * 100)))
    with open(os.path.join(path_to_save, file_name), "wb") as f:
        f.write(fh.getvalue())
    fh.close()


def load_files(drive, client_id, reason):
    status = dict()
    files, origs = list_files(drive)
    test_dir = 'index_files'
    if not os.path.exists(test_dir + '/' + client_id):
        os.makedirs(test_dir + '/' + client_id)
    with open(test_dir + '/' + 'files' + client_id, "w") as json_file:
        json.dump(files, json_file)
    with open(test_dir + '/' + 'origs' + client_id, "w") as json_file:
        json.dump(origs, json_file)
    for file_ in files:
        gdrive_download_file(drive, file_, files[file_][0], test_dir + '/' + client_id)
    if 'duplicates' in reason:
        status['duplicates'] = check_for_duplicates(test_dir + '/' + client_id, client_id, files, origs)
    if 'index' in reason:
        files_data = dict()
        for file in os.scandir(test_dir + '/' + client_id):
            strings = get_file_strings(file.path)
            if strings:
                files_data[file.name] = strings
        inverted_index = build_inverted_index(files_data)
        status['inverted_index'] = 1
        with open(test_dir + '/' + 'index' + client_id, "w") as json_file:
            json.dump(inverted_index, json_file)
    shutil.rmtree(test_dir + '/' + client_id)
    return status


def search(query, client_id):
    test_dir = 'index_files'
    with open(test_dir + '/' + 'files' + client_id) as json_file:
        files = json.load(json_file)
    with open(test_dir + '/' + 'origs' + client_id) as json_file:
        origs = inverted_index = json.load(json_file)
    with open('index_files' + '/' + 'index' + client_id) as json_file:
        inverted_index = json.load(json_file)
    r = find(query, inverted_index)
    query_results = []
    if r is not None:
        for result in r:
            for id_ in files:
                if files[id_][0] == result:
                    query_results.append({
                        'id': id_,
                        'name': origs[id_][0],
                        'name_on_disk': result,
                        'modified_time': origs[id_][1],
                        'url': origs[id_][2]
                    })
        return query_results
    else:
        return []


def get_file_strings(path):
    # print("\n*********", path, "********\n")
    # split the extension from the path and normalise it to lowercase.
    ext = os.path.splitext(path)[-1].lower()
    # extract with textract for these data types
    if ext == '.docx':
        try:
            texts = str(textract.process(path, encoding='utf-8')).replace('\\n', '\n').replace('\\r', '').split('\n')
        except:
            return None
    # for txt data, use standard file read
    elif ext == '.txt':
        try:
            # first detect file encoding
            with open(path, 'rb') as file:
                rawdata = file.read()
                result = chardet.detect(rawdata)
                charenc = result['encoding']
                # print(charenc)
                # then read it
                with open(path, 'r', encoding=charenc) as file:
                    texts = file.readlines()
        except:
            return None
    else:
        return None
    return texts


def is_word(word):
    english_stopwords = set(stopwords.words("english"))
    return word.isalpha() and word not in english_stopwords


def preprocess(sent):
    prep = nltk.word_tokenize(sent.lower())
    prep = [w for w in prep if is_word(w)]
    return prep


def build_inverted_index(files_data):
    inverted_index = {}
    for name, strings in files_data.items():
        tokens = preprocess(' '.join(strings).lower())
        file_index = Counter(tokens)
        # update global index
        for term in file_index.keys():
            file_freq = file_index[term]
            if term not in inverted_index:
                inverted_index[term] = [(name, file_freq)]
            else:
                inverted_index[term].append((name, file_freq))
    return inverted_index


def find(query, index):
    postings = []
    query_tokens = preprocess(query.lower())
    for token in query_tokens:
        token_ = fix_typo_norvig(token)
        if token_ not in index:
            continue
        posting = index[token_]
        posting = [i[0] for i in posting]
        postings.append(posting)
    if len(postings) == 0:
        return None
    else:
        docs = set.intersection(*map(set, postings))
        return docs
