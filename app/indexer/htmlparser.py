# SPDX-FileCopyrightText: 2022 PeARS Project, <community@pearsproject.org>
#
# SPDX-License-Identifier: AGPL-3.0-only

import re
import logging
from os.path import join
import requests
import justext
from bs4 import BeautifulSoup
from langdetect import detect
from app import LANGS, AUTH_TOKEN, OMD_PATH
from app.indexer import detect_open
from app.api.models import installed_languages


def remove_boilerplates(response, lang):
    text = ""
    paragraphs = justext.justext(
        response.content,
        justext.get_stoplist("English"), #FIX FOR MULTIPLE LANGUAGES
        max_link_density=0.3,
        stopwords_low=0.1,
        stopwords_high=0.3,
        length_low=30,
        length_high=100)
    for paragraph in paragraphs:
        #if not paragraph.is_boilerplate:
        text += paragraph.text + " "
    return text


def BS_parse(url):
    req = None
    try:
        if url.endswith('?direct'):
            req = requests.get(url, timeout=10, headers={'Authorization': 'token:'+AUTH_TOKEN})
        else:
            req = requests.get(url, timeout=10)
        req.encoding = 'utf-8'
    except Exception:
        print("Request failed when trying to index", url, "...")
        return False, req
    if req.status_code != 200:
        print("Failure on status code",req.status_code)
        logging.exception("Warning: " + str(req.url) + ' has a status code of: ' + str(req.status_code) + ' omitted from database.\n')
        return False, req
    bs_obj = BeautifulSoup(req.text, "lxml")
    #print(bs_obj.prettify())
    return bs_obj, req


def extract_links(url):
    links = []
    print("Extracting links from",url)
    # Ensure we only process OMD links (we should anyway, but you never know...)
    if not url.startswith(OMD_PATH):
        return links
    try:
        if url.endswith('?direct'):
            req = requests.get(url, timeout=10, headers={'Authorization': 'token:'+AUTH_TOKEN})
        else:
            req = requests.get(url, timeout=10)
        if "text/html" not in req.headers["content-type"]:
            print(url, "not a HTML document...")
            return links
    except Exception:
        return links
    bs_obj = BeautifulSoup(req.text, "lxml")
    if not bs_obj:
        return links
    hrefs = bs_obj.findAll('a', href=True)

    #Clean base url
    ref = url.replace(OMD_PATH,'/').replace('?direct','')
    for h in hrefs:
        if h['href'].startswith(ref):
            links.append(join(OMD_PATH,h['href'][1:]))
    return links


def extract_html(url):
    '''From history info, extract url, title and body of page,
    cleaned with BeautifulSoup'''
    title = None
    body_str = ""
    snippet = ""
    language = LANGS[0] #Hack
    error = None
    bs_obj, req = BS_parse(url)
    if not bs_obj:
        logging.error(f"\t>> ERROR: extract_html: Failed to get BeautifulSoup object.")
        title = ""
        return title, body_str, snippet, language
    if url.startswith('http'):
        og_title = bs_obj.find("meta", property="og:title")
        og_description = bs_obj.find("meta", property="og:description")
        #print(f"OG TITLE {og_title}")
        #print(f"OG DESC {og_description}")

        # Process title
        if og_title:
            title = og_title['content']
        else:
            h1s = bs_obj.findAll('h1')
            if len(h1s) > 0:
                title = h1s[0].text

        if og_description:
            body_str = ' '.join(og_description['content'].split()[:100])
        ps = bs_obj.findAll(['h1','h2','h3','h4','p','span'])
        for p in ps:
            text = re.sub(r'{{[^}]*}}','',p.text.strip())
            text = text.strip().replace('\n',' ')
            if text not in ['',':']:
                #print("<text>",text,"</text>")
                body_str+=text+' '
        #print("BODY",body_str)
        try:
            language = detect(title + " " + body_str)
            logging.debug(f"\t>> INFO: Language for {url}: {language}")
        except Exception:
            # Note, language will be assumed to be LANGS[0]
            logging.error(f"\t>> ERROR: extract_html: Couldn't detect page language.")


        # Process snippet
        if og_description:
            snippet = ' '.join(og_description['content'].split()[:100])
        else:
            snippet = ' '.join(body_str.split()[:10]) #10 to conform with EU regulations
    #print(title, body_str[:100])
    if not title:
        title = ' '.join(body_str.split()[:7])
    return title, body_str, snippet, language


def extract_txt(url):
    logging.info(f">> INDEXER: HTMLPARSER: extract_txt: url: {url}")
    title = url.split('/')[-1].split("?")[0] # read after the last slash, title is everything until any parameters (e.g. "?totext")
    body_str = ""
    snippet = ""
    language = LANGS[0]
    logging.debug(f">> INDEXER: HTMLPARSER: extract_txt: title: {title}")
    try:
        req = requests.get(url, timeout=120, headers={'Authorization': 'token:'+AUTH_TOKEN})
        req.encoding = 'utf-8'
    except Exception:
        return title, body_str, snippet, language
    body_str = req.text
    logging.debug(f">> INDEXER: HTMLPARSER: extract_txt: body: {body_str[:100]}")
    try:
        language = detect(body_str)
        logging.debug(f">> INDEXER: HTMLPARSER: extract_txt: language: {language}")
    except Exception:
        logging.error(f">> ERROR: INDEXER: HTMLPARSER: extract_txt: couldn't detect page language for {url}.")

    snippet = ' '.join(body_str.split()[:50]).replace(',', '-')
    return title, body_str, snippet, language
