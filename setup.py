from setuptools import setup

setup(
    name="ouxml_link_checker",
    packages=['ouxml_link_checker'],
    version='0.0.4',
    author="Tony Hirst",
    author_email="tony.hirst@gmail.com",
    description="Simple link checker for OU-XML.",
    long_description='''
    Tools for link checking links found in OU-XML documents.
    ''',
    long_description_content_type="text/markdown",
    install_requires=[
        'click',
        'requests',
        'tqdm',
        'lxml'
    ],
    extras_require={
        'webshot': ['selenium', 'webdriver-manager']
    },
    entry_points='''
        [console_scripts]
        ouxml_tools=ouxml_link_checker.cli:cli
    '''

)
