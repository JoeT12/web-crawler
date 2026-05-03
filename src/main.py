from crawler import Crawler
from indexer import Indexer
from search import Search

import logging


def main():
    initial_seeds = ["https://quotes.toscrape.com"]

    # Logging Configuration.
    logging.basicConfig(
        level=logging.INFO,
        # Format of the logs to be printed out.
        format="%(levelname)s | %(name)s.%(funcName)s() | %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Module initalisations.
    indx = Indexer(logger=logger)
    crawler = Crawler(seeds=initial_seeds, logger=logger,
                      crawl_limit=250, indexer=indx)
    search = Search(logger=logger, indexer=indx)

    # Keep track of whether the index is loaded or not to prevent errors.
    loaded_index = False

    # 'Shell'.
    while True:
        # Get the command from the standard input.
        cmd = input(">> ")

        # Break on exit command.
        if cmd == "exit":
            break

        # Start the crawl when build command used.
        if cmd == "build":
            crawler.crawl()
            loaded_index = True

        # Load the index when the load command is used.
        if cmd == "load":
            indx.load_index()
            loaded_index = True

        # Perform a query search when the find command is used.
        if cmd.startswith("find "):
            if loaded_index:
                query = cmd[5:]
                print(search.search_query(query))
            else:
                print(
                    "You must load the index before executing the find command")

        # Perform a single term search when the print command is used.
        if cmd.startswith("print "):
            if loaded_index:
                term = cmd[6:]
                print(search.search_term(term))
            else:
                print(
                    "You must load the index before executing the print command")


# Only call main if this file is directly invoked.
if __name__ == "__main__":
    main()
