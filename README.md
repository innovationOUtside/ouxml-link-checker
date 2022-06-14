# ouxml-link-checker
Scrape links from OU-XML and run link checks over them 

`pip3 install --upgrade https://github.com/innovationOUtside/ouxml-link-checker/archive/refs/heads/main.zip`



Usage is:

`ouxml_tools link-check PATH/TO/DIR/CONTAINING/OU-XML_FILES`

If you are in the directory containing the OU-XML files, you can simply run:

`ouxml_tools link-check`

If the you are in a directory that contains a directory (eg `xmldocs`) that contains the OU-XML docs, you can run:

`ouxml_tools link-check xmldocs`

(or replace the name of the directory with the name of your own directory; if the directory name has spaces, specifiy it in quotes, for example `ouxml_tools link-check "OU-XML docs"`).

There's a csv file report generated at `broken_links_report.csv` and complete reports in `all_links_report.json` and `broken_links_report.json`

Preview of code and sample outputs of intermediate functions: [`link_checker.ipynb`](https://github.com/innovationOUtside/ouxml-link-checker/blob/main/link_checker.ipynb) (and a [preview of the same notebook](https://nbviewer.jupyter.org/github/innovationOUtside/ouxml-link-checker/blob/main/link_checker.ipynb) that actually works if/when Github tells you that *Something went wrong*...).


## Archiving Links

Call with the `--archive / -a` switch to submit URLs to the Internet Archive for archiving. Only files that generate a 200-OK in the final step will be submitted for archiving. Call with the `--strong-archive / -A` flag and all URLs that do not return a 404 will be submitted for archiving. (Probably need better policies here...)

### Link Archiving API

Links can be archived via a simple API that checks the links first:

```python
from ouxml_link_checker import link_checker as olc

urls=["https://www.bbc.co.uk", "https://www.open.ac.uk", "http://ww.open.ac.uk/dfhje", "https://www.open.ac.uk/dfhje"]
reps = olc.check_multiple_links(urls)
reps
```

For example, returns:

```text
{'https://www.open.ac.uk/dfhje': [(False,
   'https://www.open.ac.uk/dfhje',
   404,
   'Not Found')],
 'http://ww.open.ac.uk/dfhje': [(False,
   'http://ww.open.ac.uk/dfhje',
   None,
   'Error resolving URL')],
 'https://www.bbc.co.uk': [(True, 'https://www.bbc.co.uk/', 200, 'OK')],
 'https://www.open.ac.uk': [(True, 'https://www.open.ac.uk/', 200, 'OK')]}
 ```

 Then run: `olc.archive_links(reps)`

 ```text
Archived: https://www.bbc.co.uk
Archived: https://www.open.ac.uk
Not archived: https://www.open.ac.uk/dfhje
Not valid URLs: http://ww.open.ac.uk/dfhje
```

The `olc.archive_links()` function also accepts `include=LIST_OF _INTS` and `exclude=LIST_OF_INTS` parameters that govern which status codes are used to select URLs for archiving. (The empty `include` list means accept all codes except explicitly excluded codes. Excluded codes are always excluded.)


## ScreenshootingLinks

Call with the `--grab-screenshots` or `-s` flag to grab screenshots of resolved links.

To grab a screenshots, the `playwright` package needs to be installed separately:

```
pip install playwright
playwright install
```

Screenshots will be saved into an automatically created `grab_link_screenshots` directory.
