# ---
# jupyter:
#   jupytext:
#     formats: ipynb,ouxml_link_checker//py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# # Link Checker for Links in OU-XML Documents
#
# The OU-XML document format is used to act as a gold master document for teaching materials published on the OU VLE and elsewhere.
#
# This script can be used to extract and check links referenced within OU-XML documents.
#
# Reports are generated as CSV files (`.csv` file suffix) that may be viewed in a text editor, or loaded into a spreadsheet application.

# ## Utility Functions
#
# Some utility functions for working with the OU-XML document and processing XML tags.

# +
# Extract all the text inside a tag, include text inside child tags

import unicodedata

def flatten(el):
    ''' Utility function for flattening XML tags. '''
    if el is None: return
    result = [ (el.text or "") ]
    for sel in el:
        result.append(flatten(sel))
        result.append(sel.tail or "")
    return unicodedata.normalize("NFKD", "".join(result)) or ' '


# -

# Iterating through a list of links and making a web request for each one can happen quickly, especially if we are just requesting page headers and not the complete contents of a page.
#
# A trick many screenscrapers use is to add a small delay between requests, often randomising the delay times to make it less obvious that a scrape is in play. THhe following function gives a minimal function that helps us play nice when creating lots of web requests.

# +
# Wait for a short random interval
# This is so we don't clobber a particular website or the network too badly!

import time
from random import random

def play_nice(delay=0.1, min_delay=0.01):
    """Add a random delay between consecutive web requests."""
    # It would probably make more sense to do this to throttle multiple requests to the same domain
    time.sleep(min_delay + delay*random())


# -

# We're going to want to get lists of XML files somehow; the following function will grab the names of files with a particular file suffix (by default, `.xml`) from a directory with a specified path:

# +
# Get a list of xml files in a folder/directory

import os
from pathlib import Path

def get_xml_files(path_str='.', suffix='.xml'):
    path = Path(path_str)
    docs = [path/x for x in os.listdir(path) if x.endswith(suffix)]
    return docs


# + tags=["active-ipynb"]
# # Example usage
# get_xml_files('./xml_test')
# -

# A nod to user feedback on long running jobs where we are perhaps waiting for lots of links to be tested, the `tqdm` package provides a simple way to create progress bars.

# Import a package that displays progress bars nicely
from tqdm import tqdm

# ## Extract Information From OU-XML
#
# Tool(s) to extract links and other information from OU-XML documents.

# To make use of the XML content in a document, we need to open the document, read its contents and then parse it into a strcuture we can work with. Sometimes, we need to clean the document text up a bit before we can parse it...

# +
# Open an XML file/document, read its contents and parse them as an XML etree object

from lxml import etree

def get_xml_from_doc(doc, clean=True):
    """Read file and parse as XML object."""
    xml = doc.read_text()
    
    if clean:
        for cleaner in ['<?sc-transform-do-oumusic-to-unicode?>',
                        '<?sc-transform-do-oxy-pi?>',
                        '<?xml version="1.0" encoding="utf-8"?>',
                        '<?xml version="1.0" encoding="UTF-8"?>',
                        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>']:
            xml = xml.replace(cleaner, '')
            
    xml_root = etree.fromstring(xml)
    return xml_root


# -

# Having got the XML into a structure we can work with, we can start to treat it like a simple database from which we can extract different sorts of infomration.
#
# OU-XML documents are structured in a particular way, so we can use prior knowledge of that structure to do things like pull out a course/module code and name, as well as the names of different sections in the document. We can use this information to help us report on where in a document we might find a particular broken link if we do discover that it is broken and in need of repair...
#
# We also want to extract the links referenced in the document; that is the point of this recipe, after all...

# +
# Extract metadata and links from a parsed OU-XML document

def parse_ouxml_metadata(courseRoot):
    """Extract some metadata from the OU-XML file."""
    _coursecode = courseRoot.find('.//CourseCode')
    coursecode = flatten(_coursecode)
    _coursetitle = courseRoot.find('.//CourseTitle')
    coursetitle = flatten(_coursetitle)

    _itemtitle = courseRoot.find('.//ItemTitle')
    itemtitle = flatten(_itemtitle)

    metadata = {'coursecode': coursecode,
                'coursetitle': coursetitle,
                'itemtitle': itemtitle,
               }
    return metadata


def extract_links_from_doc(courseRoot, unique_links=None):
    """Extract links from OU-XML document."""
    unique_links = [] if unique_links is None else unique_links
    links = {}

    # Grab some metadata
    metadata = parse_ouxml_metadata(courseRoot)
    sessions = courseRoot.findall('.//Session')
    
    for session in sessions:
        _links = []
        session_title = flatten(session.find('.//Title'))
        
        for l in session.findall('.//a'):
            _lhref = l.get('href').replace('.libezproxy.open.ac.uk','')
            if l not in unique_links:
                unique_links.append(_lhref)
                _links.append((flatten(l), _lhref))

        links[session_title] = _links

    # <BackMatter>
    backmatter = courseRoot.find('.//BackMatter')
    _links = []
    for l in backmatter.findall('.//a'):
        _lhref = l.get('href').replace('.libezproxy.open.ac.uk','')
        if l not in unique_links:
            unique_links.append(_lhref)
            _links.append((flatten(l), _lhref))
    links['BackMatter'] = _links
    
    doc_links = {'metadata': metadata, 'sessions': links}
    
    return doc_links, unique_links


# -

# We can extract the links from a set of documents by extracting the links from each separate document in turn.
#
# For convenience, we return two objects:
#
# - a growing list of unique URLs we need to test;
# - a list of URLs associated with each OU-XML document, broken down by session.
#
# Note: there is also the notion of a `Unit` block element in the OU-XML definition but that is not currently parsed as a particular unit of organisation.

# +
# Extract all the links from a set of documents

def extract_links_from_docs(docs):
    """Process a set of OU-XML documents and extract unique links from them all."""
    docs = docs if isinstance(docs, list) else [docs]
    unique_links = []
    doc_links = []
    for doc in docs:
        xml = get_xml_from_doc(doc)
        _doc_links, unique_links = extract_links_from_doc(xml, unique_links)
        _doc_links['metadata']['file'] = str(doc)
        doc_links.append(_doc_links)
        
    return doc_links, unique_links


# + tags=["active-ipynb"]
# docs = get_xml_files('./xml_test')
# doc_links, unique_links = extract_links_from_docs(docs)
#
# unique_links, doc_links
# -

# ## Link Checker
#
# A simple routine to check links. The link check will report on:
#
# - broken links (404);
# - temporary and permanent redirects;
# - links using OU authentication (libezproxy; link domains are suffixed by `.libezproxy.open.ac.uk`) will have the libezproxy component stripped;
# - links using liblinks (of the form `https://www.open.ac.uk/libraryservices/resource/website:ID&amp;f=FID`; the `f=FID` seems redundant - what does it do?)
#
# *TO DO: where appropriate/informative, consider reports for the full range of [`2xx` success](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#2xx_success) reponse codes, [`3xx` redirection](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#3xx_redirection) codes, [`4xx` client error](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#4xx_client_errors) codes and [`5xx` server error](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#5xx_server_errors) codes.*

# +
# Run a link check on a single link

import requests

def link_reporter(url, display=False, redirect_log=True):
    """Attempt to resolve a URL and report on how it was resolved."""
    if display:
        print(f"Checking {url}...")
    
    # Make request and follow redirects
    try:
        r = requests.head(url, allow_redirects=True)
    except:
        r = None
    
    if r is None:
        return [(False, url, None, "Error resolving URL")]

    # Optionally create a report including each step of redirection/resolution
    steps = r.history + [r] if redirect_log else [r]
    
    step_reports = []
    for step in steps:
        step_report = (step.ok, step.url, step.status_code, step.reason)
        step_reports.append( step_report )
        if display:
            txt_report = f'\tok={step.ok} :: {step.url} :: {step.status_code} :: {step.reason}\n'
            print(txt_report)

    return step_reports


# -

# We can run some simple tests to see examples of particular sorts of errors. Other errors may be discovered when running the link checker over a wider range of resources.
#
# We could capture and report on different sorts of status code in specific ways, if that is useful.

# + tags=["active-ipynb"]
# ## Test link check reports
# url_direct='https://rallydatajunkie.com/visualising-rally-stages/'
# url_redirect='http://rallydatajunkie.github.io/visualising-rally-stages/'
# url_liblink='https://www.open.ac.uk/libraryservices/resource/website:106223&amp;f=28585'
# url_404='http://www.digitalhealth.net/news/25742/'
# url_ezproxy='http://ieeexplore.ieee.org.libezproxy.open.ac.uk/xpl/articleDetails.jsp?arnumber=4376143'
# url_ezproxy_clean=url_ezproxy.replace('.libezproxy.open.ac.uk', '')
#
# link_reporter(url_direct)
# link_reporter(url_redirect)
# link_reporter(url_liblink)
# link_reporter(url_404)
# link_reporter(url_ezproxy)
# link_reporter(url_ezproxy_clean)
# -

# ## Checking Links from One or More Documents
#
# A routine to check links from OU-XML documents found in a directory:

# +
# Run link checks over a set of links

def check_multiple_links(urls, display=False, redirect_log=True):
    """Check multiple links."""
    
    # Use unique links
    urls = list(set(urls)) if isinstance(urls, list) else [urls]
    
    link_reports = {}
    for url in tqdm(urls):
        play_nice()
        link_report = link_reporter(url, display, redirect_log)
        link_reports[url] = link_report
        
    return link_reports


# + tags=["active-ipynb"]
# # Test a set of links
# test_links = [url_direct, url_redirect, url_404]
#
# link_reports = check_multiple_links(test_links, display=True)
# link_reports
# -

# From the set of links, we can create a report showing any dead links:

# +
# Find dead links

def dead_link_report(link_reports):
    """Create a list of dead links."""
    dead_links = {}
    
    for link in link_reports:
        link_report = link_reports[link]
        if not link_report[-1][0]:
            dead_links[link] = link_report

    return dead_links



# + tags=["active-ipynb"]
# dead_link_report(link_reports)
# -

# We can also create a report per document. This is perhaps more useful because we can see which sections contain which dead links, if any.

def link_reporter_by_docs(doc_links):
    """Link reports by document."""
    doc_links_reports = []
    doc_links_nok_reports = []
    
    for doc in doc_links:
        doc_links_report = {'metadata': doc['metadata'], 'sessions': {}}
        doc_links_nok_report = {'metadata': doc['metadata'], 'sessions': {}}
        
        for session in tqdm(doc['sessions']):
            link_reports = []
            nok_link_reports = []
            for (title, url) in doc['sessions'][session]:
                play_nice()
                link_report = link_reporter(url)
                ok = link_report[-1][0]
                link_reports.append( (title, url, link_report, ok))
                
                if not ok:
                    nok_link_reports.append( (title, url, link_report, ok))

            doc_links_report['sessions'][session] = link_reports
            if nok_link_reports:
                doc_links_nok_report['sessions'][session] = nok_link_reports

        doc_links_reports.append(doc_links_report)
        doc_links_nok_reports.append(doc_links_nok_report)
        
    return doc_links_reports, doc_links_nok_reports


# + tags=["active-ipynb"]
# link_reports, bad_link_reports = link_reporter_by_docs(doc_links)

# + tags=["active-ipynb"]
# bad_link_reports
# -

# Whilst the JSON file is convenient for storing data, and easy to work with if you know how, a tabular CSV report is probably more useful in many cases.
#
# The following is a first quick attempt at a report that contains enough information to be useful when it comes to finding which section of which file each broken link appears in.

# +
# Crude output report broken link

import csv

def simple_csv_report(links_report, outf='link_report.csv'):
    """Generate a simple CSV link check report."""

    with open(outf, 'w') as f:
        write = csv.writer(f)
        cols = ['file', 'code', 'title', 'item', 'session', 'linktext', 'link', 'error']
        write.writerow(cols)

        for link_report in links_report:
            row_base = [link_report['metadata']['file'],
                        link_report['metadata']['coursecode'],
                        link_report['metadata']['coursetitle'],
                        link_report['metadata']['itemtitle']]

            rows = []
            for session in link_report['sessions']:
                for link in link_report['sessions'][session]:
                    row = row_base + [session, link[0], link[1], link[2][-1][-2]]
                    rows.append(row)
 
            write.writerows(rows) 


# + tags=["active-ipynb"]
# simple_csv_report(bad_link_reports)
# !cat link_report.csv
# -

# To try to make things easier to use, we also define (in the `cli.py` file) a simple command line interface that can call the following function, with a directory path, to run the link checker over links extracted form the `.xml` files in the specified directory.
#
# Usage on the command line is then of the form:
#
# `ouxml_tools link-check PATH/TO/DIR/CONTAINING/OU-XML_FILES`
#
# with three output reports generated:
#
# - a csv file report containing minimal broken link information (`broken_links_report.csv`);
# - complete reports of all link resolution traces and just the broken link resoution traces in `all_links_report.json` and `broken_links_report.json` respectively.

# +
import json
import urllib.parse


def archive_link(url):
    """Submit link archive request to Interet Archive."""

    quoted_url = urllib.parse.quote(url)
    url_ = f"https://web.archive.org/save/{quoted_url}"
    # Should probably capture response and generate archive request report
    r = requests.get(url_, allow_redirects=True)
    return url, r

def archive_links(link_reports, include=None, exclude=None):
    """Submit each unique link in a link report dictionary to the Internet Archive."""
    include = [] if include is None else include
    exclude = [] if exclude is None else exclude
    archived = []
    not_archived = []
    not_valid_url = []
    excluded_url = []
    link_reports_ = []

    # Generate a list of links we want to archive
    for link_ in link_reports:
        # Get status report of last step in forwarded request
        status = link_reports[link_][-1][2]
        if status is None:
            not_valid_url.append(link_)
            continue
        # We don't want excluded report status links
        if status not in exclude:
            # We want all links or just included links
            if not include or status in include:
                link_reports_.append(link_)
        else:
            excluded_url.append(link_)

    for link_ in tqdm(link_reports_):
        url, response = archive_link(link_)
        if response.ok:
            archived.append(url)
        else:
            not_archived.append(url)
        play_nice()

    for url in archived:
        print(f"Archived: {url}")
    for url in not_archived:
        print(f"Not archived: {url}")
    for url in excluded_url:
        print(f"Excluded: {url}")
    for url in not_valid_url:
        print(f"Not valid URLs: {url}")
    

def link_check_reporter(path, archive=False, strong_archive=False, display=False, redirect_log=True):
    """Run link checks."""
    docs = get_xml_files(path)
    doc_links, unique_links = extract_links_from_docs(docs)

    link_reports, bad_link_reports = link_reporter_by_docs(doc_links)

    with open('all_links_report.json', 'w') as f:
        json.dump(link_reports, f)

    with open('broken_links_report.json', 'w') as f:
        json.dump(bad_link_reports, f)

    simple_csv_report(bad_link_reports, outf='broken_links_report.csv')

    if archive or strong_archive:
        print("Archiving links...")
        if strong_archive:
            archive_links(link_reports, exclude=[404])
        elif archive:
            archive_links(link_reports, include=[200])