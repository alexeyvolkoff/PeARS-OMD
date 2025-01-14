# SPDX-FileCopyrightText: 2023 PeARS Project, <community@pearsproject.org>, 
#
# SPDX-License-Identifier: AGPL-3.0-only

# Import flask dependencies
import logging
import joblib
import numpy as np
from scipy import sparse
from math import ceil
from flask import (Blueprint,
                   flash,
                   request,
                   render_template,
                   Response)

from app import LANG, VEC_SIZE, tracker
from app.api.models import Urls
from app.indexer.neighbours import neighbour_urls
from app.indexer import mk_page_vector, spider
from app.utils import readDocs, readUrls, get_language, init_pod, init_podsum, carbon_print
from app.utils_db import pod_from_file
from app.indexer.htmlparser import extract_links, extract_html
from app.indexer.posix import posix_doc
from app.auth.controllers import login_required
from os.path import dirname, join, realpath, isfile

dir_path = dirname(dirname(realpath(__file__)))
pod_dir = join(dir_path,'static','pods')

# Define the blueprint:
indexer = Blueprint('indexer', __name__, url_prefix='/indexer')


# Set the route and accepted methods
@indexer.route("/", methods=["GET", "POST"])
@login_required
def index():
    num_db_entries = len(Urls.query.all())
    if request.method == "GET":
        return render_template(
            "indexer/index.html", num_entries=num_db_entries)


'''
 Controllers for various ways to index
 (from file, from url)
'''

@indexer.route("/from_crawl", methods=["GET","POST"])
@login_required
def from_crawl():
    keyword = "home" #hard-coded
    lang = LANG
    init_pod(keyword)
   
    def process_start_url(u):
        print("Now crawling", u)
        f = open(join(dir_path, "urls_to_index.txt"), 'w')
        f.write(u + ";" + keyword + ";" + lang +"\n")
        f.close()

    if request.method == "POST":
        u = request.form['url']
        process_start_url(u)
        return render_template('indexer/progress_crawl.html')
    else:
        u = request.args['url']
        process_start_url(u)
        return progress_crawl()



@indexer.route("/from_docs", methods=["POST"])
@login_required
def from_docs():
    print("DOC FILE:", request.files['file_source'])
    if request.files['file_source'].filename[-4:] == ".txt":
        keyword = request.form['docs_keyword']
        keyword, lang = get_language(keyword)
        file = request.files['file_source']
        file.save(join(dir_path, "docs_to_index.txt"))
        f = open(join(dir_path, "keyword_lang.txt"), 'w')
        f.write(keyword+'::'+lang+'\n')
        f.close()
        return render_template('indexer/progress_docs.html')





'''
Controllers for progress pages.
One controller per ways to index (file, crawl).
The URL indexing uses same progress as file.
'''

@indexer.route("/progress_crawl")
@login_required
def progress_crawl():
    print("Running progress crawl")
    urls, keywords, langs, errors = readUrls(join(dir_path, "urls_to_index.txt"))
    if urls:
        url = urls[0]
    else:
        url = None
    print("Calling spider on",url)
    spider.write_docs(url) #Writing docs to docs_to_index.txt


    def generate():
        
        kwd = 'home' #hard-coded - change if needed
        lang = LANG
        print("\n\n>>> INDEXER: CONTROLLER: READING DOCS")
        urls, titles, snippets, descriptions, docs = readDocs(join(dir_path, "docs_to_index.txt"))
        pod_name = kwd+'.npz'
        pod_dir = join(dir_path,'static','pods')

        #Checking matrix files
        if not isfile(join(pod_dir,'podsum.npz')):
            init_podsum()
        if not isfile(join(pod_dir,pod_name)):
            pod = np.zeros((1,VEC_SIZE))
            pod = sparse.csr_matrix(pod)
            sparse.save_npz(join(pod_dir,pod_name), pod)

        c = 0
        if tracker != None:
            task_name = "run indexing for "+str(len(urls))+" files"
            tracker.start_task(task_name)
        for url, title, snippet, description, doc in zip(urls, titles, snippets, descriptions, docs):
            print("\n\n>>> INDEXER: CONTROLLER: PROGRESS CRAWL: INDEXING", url)
            success, podsum, text, doc_id = mk_page_vector.compute_vectors_local_docs(url, title, snippet, description, doc, kwd, lang)
            if success:
                posix_doc(text, doc_id, kwd)
                pod_from_file(kwd, lang, podsum)
            else:
                print("\n\n>>> INDEXER: CONTROLLER: PROGRESS CRAWL: ERROR INDEXING", url)
            c += 1
            print('###', str(ceil(c / len(urls) * 100)))
            yield "data:" + str(ceil(c / len(urls) * 100)) + "\n\n"
        if tracker != None:
            search_emissions = tracker.stop_task()
            carbon_print(search_emissions, task_name)

    return Response(generate(), mimetype='text/event-stream')



