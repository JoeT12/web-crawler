from crawler import Crawler
import logging
import argparse


def main():
    initial_seeds = ["https://quotes.toscrape.com"]

    # CLI Argument Configuration.
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="Command for the Crawler")
    args = parser.parse_args()

    # Logging Configuration.
    logging.basicConfig(
        level=logging.INFO,
        # Format of the logs to be printed out.
        format="%(levelname)s | %(name)s.%(funcName)s() | %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Build Command.
    if args.command == "build":
        crawer = Crawler(seeds=initial_seeds, logger=logger)
        crawer.crawl()


if __name__ == "__main__":
    main()