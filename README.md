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

 
