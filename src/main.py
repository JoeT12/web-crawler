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
    crawer = Crawler(seeds=initial_seeds, logger=logger, crawl_limit=10000)
    indx = Indexer(logger=logger)
    search = Search(logger=logger, indexer=indx)

    # 'Shell'.
    while True:
        # Get the command from the standard input.
        cmd = input(">> ")

        # Break on exit command.
        if cmd == "exit":
            break

        # Start the crawl when build command used.
        if cmd == "build":
            crawer.crawl()

        # Load the index when the load command is used.
        if cmd == "load":
            indx.load_index()

        # Perform a query search when the find command is used.
        if cmd.startswith("find "):
            query = cmd[5:]
            print(search.search(query))

        #  Perform a single term search when the print command is used.
        if cmd.startswith("print "):
            term = cmd[6:]
            tokens = indx.tokenise_tag_content([term])
            for token in tokens:
                print(token, indx.get_inverted_index(token))


if __name__ == "__main__":
    main()
