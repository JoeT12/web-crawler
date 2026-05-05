# Web Crawler

## Project Summary
This repository contains a web crawler application that was developed as part of the `COMP3011 Web Services and Web Data` course at the University of Leeds. It allows the automated crawling of pages on the web to enable search engine functionality that is accessed via a shell.

## Setup
### Installing Python
To set up and execute the crawler, you will need a Python runtime installed on your local machine. To download Python, please navigate [here](https://www.python.org/downloads/). Once downloaded, Python will need to be added to your system path.
### Cloning the Repository
You will also need to clone the application repository. For a guide on how to do this, please navigate [here](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

## Running the Crawler
Once the repository has been cloned, navigate to the repository on your local machine using a terminal session. Once in the root directory of the cloned repository, run the following commands:
1. `pip install -r requirements.txt`: To install the crawler dependencies.
2. `python src/main.py`: To start the Crawler shell.
Once the application has been set up and invoked, you should see a `>>` displayed in the terminal. This means the program is ready for you to input your command.

## Commands / Usage
1. `build`: The build command will begin the web crawling process, with the seed URLs specified in [main.py](src/main.py). It will crawl a fixed number of pages, which can also be adjusted in the same file. Example usage is just the command with no additional arguments: `build`.
2. `load`: The load command will load the inverted index and the document map stored on disk into the application memory, to allow search. Example usage is just the command with no additional arguments: `load`.
3. `print`: The print command will take a single argument: a single term and return the inverted index posting for that term (if it exists). Example usage: `print hello`.
4. `find`: The find command will take a search query as an argument, and return all pages that are relevant to the query. Example usage: `find quotes`.
5. `exit`: The exit command will terminate the web crawler shell. Example usage is just the command with no additional arguments: `exit`.
On commands 1-4, log messages from the modules will be displayed.

We note that to use the `print` or `find` commands, either the `build` or `load` commands must be executed first to populate the in-memory inverted index structure.

## Architecture Overview
### src/ Directory
The src directory contains the following modules:
1. `crawler.py`: This handles all web crawling functionality.
2. `indexer.py`: This handles all indexing functionality.
3. `search.py`: This handles all searching functionality within the index.
4. `main.py`: This is the entry point to the crawler and implements the shell logic.

### data/ Directory
The data directory contains the following files (when a crawl has been completed):
1. `documents.json`: This contains a map of document IDs to URLs.
2. `index.json`: This contains the inverted index.

### tests/ Directory
The tests directory contains the following modules:
1. `test_crawler.py`: This contains unit tests for the crawler module.
2. `test_indexer.py`: This contains unit tests for the indexer module.
3. `test_search.py`: This contains unit tests for the search module.

### .github/ Directory
This directory contains a single directory called `workflows/`. Within this sub-directory, there is a file called `tests.yml` that is used by GitHub to trigger the automated tests and coverage report on a commit or pull request. We note that this same file also configures the workflow to perform a PEP 8 check on all code in the `src/` directory to ensure that code quality is being upheld.

## Design Decisions
### Inverted Index Storage Format
The inverted index was stored in JSON due to the index being stored in a Python dictionary when stored in memory by the crawler, and JSON mapping almost identically to this format. Other languages considered included YAML, but this was left out to make the storage functionality clearer.

### Data Structures
The data structures chosen were as follows:
1. Frontier: A Python `dict` made up of host keys and URL queues. This enables the crawler to group all URLs on the frontier together per host, allowing us to enforce a politeness window on sequential requests to the same host. We note that the queue for each host uses a Python `deque` to implement a FIFO queue. The alternative would have been to use a Python `list`, but this structure is not optimised for removal of the first element and hence would have incurred performance overheads. An example of the frontier structure is shown below:
```python
{
    "www.google.com": {
        "queue": deque([
            "https://www.google.com/",
            "https://www.google.com/about"
        ]),
        "last_accessed": None
    },
    "www.bbc.com": {
        "queue": deque([
            "https://www.bbc.com/news"
        ]),
        "last_accessed": None
    }
}
```
2. Inverted Index: A Python `dict`. This structure supports the storage of nested key-value pairs, which gave flexibility in implementing the index. Within the dictionary, each token is mapped to the documents that contain it, and the features of the token in that document are mapped to each document. We note that we denote documents in this structure with a numeric ID, which is mapped to a URL in a separate structure. This enables the searching functionality, which requires numeric comparisons. An example of the in-memory inverted index is shown below:
```python
{
    "search": {
        1: {"term_frequency": 2, "positions": [4, 15], "fields": ["title", "body"], "score": 6.2},
        2: {"term_frequency": 1, "positions": [9], "fields": ["body"], "score": 1.8}
    },
    "engin": {
        1: {"term_frequency": 1, "positions": [5], "fields": ["title"], "score": 5.0}
    }
}
```
3. Document ID Map: A Python `dict`. This stores the mapping from numeric document IDs to their corresponding URLs. An example of the document ID map is shown below:
```python
{
    1: "https://www.google.com/",
    2: "https://www.bing.com/",
    3: "https://www.bbc.com/news"
}
```
4. Seen URLs List: A Python `set`. This stores URLs that have already been discovered, preventing them from being added to the frontier multiple times. A set was chosen for retrieval efficiency and to prevent us from storing the same URL twice accidentally. An example of the seen URLs set is shown below:
```python
{
    "https://www.google.com/",
    "https://www.google.com/about",
    "https://www.bbc.com/news"
}
```
5. Disallowed Host List: A Python `set`. This stores hosts that have been disallowed by `robots.txt`, preventing the crawler from repeatedly checking or attempting to crawl them. A set was chosen for retrieval efficiency and to prevent us from storing the same host twice accidentally. An example of the disallowed hosts set is shown below:
```python
{
    "www.facebook.com",
    "www.linkedin.com"
}
```

### Notable Features
1. **Multithreaded Search Optimisations**: To optimise the searching process, we guided GenAI to use a multithreaded approach to searching. This should result in much faster querying.
2. **Host-based frontier structure**: Enabling adherence to the 6-second politeness window.
3. **Robots.txt Handling**: Before crawling a page, the crawler downloads the robots.txt file of a host to ensure the host allows crawling. If not, it is added to the disallowed hosts list to avoid additional downloads.
4. **URL Optimisations**: The URLs are normalised to prevent treating fragments as separate pages, and a seen URLs set is kept to prevent the same URL from being added to the frontier twice.
5. **Document-at-a-time Ranking**: The document-at-a-time approach is used to handle search queries, to minimise memory usage.
6. **TFIDF Search Ranking**: Upon submission of a search query, the crawler will compare and rank the documents returned using the term-frequency inverse-document-frequency (TFIDF) formula. The TFIDF score of a document is combined with topical document features (which are stored within the index). Documents containing the query terms more prominently and more distinctively are ranked higher. Reference: [TFIDF]( https://en.wikipedia.org/wiki/Tf%E2%80%93idf).
7. **PEP 8 Code Styling**: The PEP 8 code style was used to format code, promoting readability.

## Testing
The crawler has been supplemented with a high coverage (`>85%`) unit testing suite. Such tests can be found in the [tests](tests/) directory.

To run the entire test suite and get a coverage percentage, simply run the command `pytest --cov=src --cov-report=term-missing tests/*.py` from the root directory of the application repository. Alternatively, a push of code to any branch of the GitHub repository also triggers an automatic run of the tests on GitHub.

## Dependencies
The dependencies used are as follows:
1. [autopep8](https://github.com/hhatto/autopep8): To style the code.
2. [requests](https://github.com/psf/requests): To send HTTP requests to download pages.
3. [beautifulsoup4](https://code.launchpad.net/beautifulsoup/): To parse HTML.
4. [validators](https://github.com/python-validators/validators): To validate URLs.
5. [nltk](https://github.com/nltk/nltk): For tokenisation capabilities.
6. [pytest](https://github.com/pytest-dev/pytest): To write unit tests.
7. [pytest-cov](https://github.com/pytest-dev/pytest-cov): To get the percentage source code coverage by the tests.

Please navigate to the [Running the Crawler](#running-the-crawler) section for information on how to install the dependencies and run the crawler.

## Generative AI Usage Acknowledgement/Declaration
We acknowledge the use of AI to help develop the code in this project. To explain the full usage of AI in each file, we have written a declaration comment at the top of all the python files where GenAI was used, explaining its exact usage for full visibility.

We also acknowledge the use of GenAI to provide structure advice, provide code examples and clean up grammar/spelling/consistency mistakes within this README.md file.

### AI Tools Used
1. **ChatGPT 5.5 Thinking Model** was used for the Python and GitHub workflow code (see usage explanations within the files), and within this README for the purposes explained above.
2. **GitHub Copilot** was also used in the `requirements.txt` and `.gitignore` files, but was disabled for all `.py` and `.yml` files.

