# Web Crawler
This repository contains a web crawler application that was developed as part of the `COMP3011 Web Services and Web Data` course at the University of Leeds. It allows the automated crawling of pages on the web to enable search engine functionality that is accessed via a shell.

## Setup Instructions
### Downloading Python and Cloning the Repository
To setup and execute the crawler, you will need a python runtime installed on your local machine. To download python, please navigate [here](https://www.python.org/downloads/). Once downloaded, python will need to be added to your system path. 

You will also need to clone the application repository. For a guide on how to do this, please navigate [here](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

### Running the Crawler Application
Once the repository has been cloned, navigate to the repository on your local machine using a terminal session. Once in the root directory of the cloned repository, run the following commands:
1. `pip install -r requirements.txt`: To install the crawler dependencies.
2. `python src/main.py`: To start the Crawler shell.

## Using the Crawler
Once the application has been setup and invoked, you should see a `>>` outputted on the terminal. This means the program is ready for you to input your command. 

### Commands and Example Usages:
1. `build`: The build command will begin the web crawling process, with the seed URL's specified in [main.py](src/main.py). It will crawl a fixed number of pages, which can also be adjusted in the same file. Example usage is just the command with no additional arguments: `build`.
2. `load`: The load command will load the entire inverted index (stored on the disk) into the application memory, to allow search. Example usage is just the command with no additional arguments: `load`.
3. `print`: The print command will take a single argument - a single term, and return the inverted index posting for that term (if it exists). Example usage: `print hello`.
4. `find`: The print command will take a search query as an argument, and return all pages that return the query terms. Example usage `find quotes`.
5. `exit`: The exit command will terminate the web crawler shell.Example usage is just the command with no additional arguments: `exit`.
On commands 1-4, log messages from the modules will be outputted.


## Testing Instructions
To run the entire test suite, simply run the command `pytest tests/*.py` from the root directory of the application repository. Alternatively, a push of code to any branch of the GitHub repository also triggers an automatic run of the tests on GitHub.

## Dependencies
The dependencies used are as follows:
1. `autopep8`: To style the code. 
2. `requests`: To send HTTP requests to download pages.
3. `beautifulsoup4`: To parse HTML.
4. `validators`: To validate a URL.
5. `nltk`: For tokenisation capabilities.
6. `pytest`: To write tests.
7. `pytest-cov`: To get the percentage coverage of code by the tests.

To install the dependencies, simply run the command `pip install -r requirements.txt` in the root directory of the application repository.

## AI Usage Acknowledgement
We acknowledge the use of AI to help develop the code in this project. To explain the use of AI in each file, we have written a very large comment at the top of all files where AI was employed, to explain its exact usage for full visibility.
