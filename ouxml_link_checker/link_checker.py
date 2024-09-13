# ---
# jupyter:
#   jupytext:
#     formats: ipynb,ouxml_link_checker//py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
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
    coursecode = flatten(_coursecode).strip()
    _coursetitle = courseRoot.find('.//CourseTitle')
    coursetitle = flatten(_coursetitle).strip()

    _itemtitle = courseRoot.find('.//ItemTitle')
    itemtitle = flatten(_itemtitle).strip()

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
        session_title = flatten(session.find('.//Title')).strip()
        
        for l in session.findall('.//a'):
            href = l.get("href")
            if not href:
                #print(f"WTF? {href} {etree.tostring(l, pretty_print=True, encoding='utf-8', method='xml').decode()}")
                continue
            _lhref = href.replace('.libezproxy.open.ac.uk','')
            if l not in unique_links:
                unique_links.append(_lhref)
                _links.append((flatten(l).strip(), _lhref))

        links[session_title] = _links

    # <BackMatter>
    backmatter = courseRoot.find('.//BackMatter')
    _links = []
    if backmatter is not None:
        for l in backmatter.findall('.//a'):
            href = l.get("href")
            if not href:
                #print(f"WTF2? {href} {etree.tostring(l, pretty_print=True, encoding='utf-8', method='xml').decode()}")
                continue
            _lhref = href.replace('.libezproxy.open.ac.uk','')
            if l not in unique_links:
                unique_links.append(_lhref)
                _links.append((flatten(l).strip(), _lhref))
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
#
# At the moment, all links are checked, even if they are duplicates.

# +
# Run a link check on a single link

import requests

def link_reporter(url, display=False, redirect_log=True, timeout=10):
    """Attempt to resolve a URL and report on how it was resolved."""
    if display:
        print(f"Checking {url}...")

    # Make request and follow redirects
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
    except:
        r = None

    if r is None:
        return [(False, url, None, "Error resolving URL")]

    # TO DO - tidy this all up;
    # - pass back response then call a response parser?
    #  - if we have a 302, recommend a move to the final response
    #  - if we fail and http, try https; if that works, recommend updates;
    #  - generate a file of recommended updates and a tool to apply them
    # if response.status_code == 302:
    #    redirected_url = response.headers.get('Location')

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
    
    unique_link_reports = {}
    
    for doc in doc_links:
        print("Trying a new doc...")
        doc_links_report = {'metadata': doc['metadata'], 'sessions': {}}
        doc_links_nok_report = {'metadata': doc['metadata'], 'sessions': {}}
        
        #for session in tqdm(doc['sessions']):
        for session in doc['sessions']:
            print(f"new session, {len(doc['sessions'][session])} urls ")
            link_reports = []
            nok_link_reports = []
            for (title, url) in doc['sessions'][session]:
                # Only request each unique URL once
                if url in unique_link_reports:
                    link_report = unique_link_reports[url]
                else:
                    play_nice()
                    print(f"trying {url}")
                    link_report = link_reporter(url)
                    unique_link_reports[url] = link_report
                ok = link_report[-1][0]
                link_reports.append( (title, url, link_report, ok))
                
                if not ok:
                    nok_link_reports.append( (title, url, link_report, ok))


            doc_links_report['sessions'][session] = link_reports
            if nok_link_reports:
                doc_links_nok_report['sessions'][session] = nok_link_reports

        doc_links_reports.append(doc_links_report)
        doc_links_nok_reports.append(doc_links_nok_report)
        print("doc done...")
    return doc_links_reports, doc_links_nok_reports, unique_link_reports


# + tags=["active-ipynb"]
# link_reports, bad_link_reports, unique_link_reports = link_reporter_by_docs(doc_links)

# + tags=["active-ipynb"]
# bad_link_reports

# + tags=["active-ipynb"]
# unique_link_reports
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
        big_rows = []
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
            big_rows = big_rows+rows
        sorted_rows=sorted(big_rows, key=lambda x: x[0])
        write.writerows(sorted_rows)


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

# ## Submitting Links to the Internet Archive
#
# To ensure that web page content is available even a website disappears, we can try to archive the content on the Internet Archive.
#
# The following function will attempt to submit a URL for archiving on the Internet Archive:

# +
import json
import urllib.parse

def archive_link(url):
    """Submit link archive request to Internet Archive."""

    quoted_url = urllib.parse.quote(url)
    url_ = f"https://web.archive.org/save/{quoted_url}"
    # Should probably capture response and generate archive request report
    r = requests.get(url_, allow_redirects=True)
    return url, r


# -

# It is more likely that we will want to submit multiple URLs to the archiver.
#
# Links with various HTTP status codes as described in the link check status report can be included or excluded from he report.

def get_valid_links(link_reports, include=None, exclude=None):
    """Generate a list of valid links from a dict with URL keys and report values."""
    include = [] if include is None else include
    exclude = [] if exclude is None else exclude
    not_valid_url = []
    excluded_url = []
    link_reports_ = []
    
    print("Finding valid links for this process...")
    # Generate a list of links we want to archive
    # Note that this is not a list of unique URLs
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
            
    return link_reports_, excluded_url, not_valid_url


def archive_links(link_reports, include=None, exclude=None):
    """Submit each unique link in a link status report dictionary to the Internet Archive."""
    archived = []
    not_archived = []

    link_reports_, excluded_url, not_valid_url = get_valid_links(link_reports, include, exclude)

    for link_ in tqdm(link_reports_):
        print(f"Archiving: {link_}")
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


# + tags=["active-ipynb"]
# archive_links(unique_link_reports)
# -

# We can generate screenshots for the links:

def screenshot_grabber(link_reports, include=None, exclude=None):
    """Grab screenshots for links."""
    import unicodedata
    import string

    valid_filename_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    char_limit = 255

    def clean_filename(filename, whitelist=valid_filename_chars, replace=None):
        # replace spaces and . by default
        replace = [" ", "."] if replace is None else replace
        filename = filename.split("://")[-1]
        for r in replace:
            filename = filename.replace(r, '_')

        # keep only valid ascii chars
        cleaned_filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()

        # keep only whitelisted chars
        cleaned_filename = ''.join(c for c in cleaned_filename if c in whitelist)
        if len(cleaned_filename)>char_limit:
            print("Warning, filename truncated because it was over {}. Filenames may no longer be unique".format(char_limit))
        return cleaned_filename[:char_limit]

    links, excluded_url, not_valid_url = get_valid_links(link_reports, include, exclude)
    
    from playwright.sync_api import sync_playwright
    img_path = "grab_link_screenshots"
    p = Path(img_path)
    p.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_page()
        for shot_url in links:
            try:
                page.goto(shot_url)
                page.screenshot(path=Path(img_path) / f"{clean_filename(shot_url)}.png")
            except:
                print(f"\t- failed to grab screenshot for {shot_url}")
        browser.close()
        print(f"\nScreenshots saved to {img_path}")


# + tags=["active-ipynb"]
# #screenshot_grabber(unique_link_reports)
# -

# We can generate the link status report for links extracted from one or more files, optionally calling the archiver, using the following function:

def link_check_reporter(path,
                        archive=False,
                        strong_archive=False,
                        grab_screenshots=False,
                        display=False, redirect_log=True):
    """Run link checks."""
    print("Getting files...")
    docs = get_xml_files(path)
    doc_links, unique_links = extract_links_from_docs(docs)

    print("Getting link statuses for each document section...")
    link_reports, bad_link_reports, unique_link_reports = link_reporter_by_docs(doc_links)

    print("Writing status reports...")
    with open('all_links_report.json', 'w') as f:
        json.dump(link_reports, f)
    simple_csv_report(link_reports, outf="all_links_report.csv")

    with open('broken_links_report.json', 'w') as f:
        json.dump(bad_link_reports, f)
    simple_csv_report(bad_link_reports, outf='broken_links_report.csv')

    if archive or strong_archive:
        print("Archiving links...")
        if strong_archive:
            archive_links(unique_link_reports, exclude=[404])
        elif archive:
            archive_links(unique_link_reports, include=[200])

    if grab_screenshots:
        print("Screengrabbing links...")
        screenshot_grabber(unique_link_reports, include=None, exclude=None)


# Via Claude.ai, then corrected
from typing import List, Dict, Any


def extract_redirects(data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    redirects = []
    for item in data:
        metadata = item["metadata"]
        for session, session_links in item["sessions"].items():
            for link_info in session_links:
                # links are the redirects/success links chain
                links = link_info[2]
                if len(links) >= 2 and links[-1][2]==200:
                    old_url = links[0][1]
                    for _link in links:
                        if _link[0] and _link[2] == 301:
                            redirects.append(
                                {
                                    "itemtitle": metadata["itemtitle"],
                                    "file": metadata["file"],
                                    "session": session,
                                    "old_url": old_url,
                                    "new_url": links[-1][1],
                                }
                            )
                            break
    return redirects


def write_redirects_report(
    redirects: List[Dict[str, str]], filename: str = "redirect_report.csv"
):
    with open(filename, "w", newline="") as csvfile:
        fieldnames = ["itemtitle", "file", "session", "old_url", "new_url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for redirect in redirects:
            writer.writerow(redirect)
