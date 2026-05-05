from collections import deque
from datetime import datetime, timedelta
from time import sleep
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from indexer import Indexer

import requests
import validators
from bs4 import BeautifulSoup

# To implement the crawler functionality, we used the lecture slides to write function stubs and
# detailed descriptions for implementation by a GenAI tool. The GenAI tool used to generate the
# implementations was ChatGPT (5.2 Thinking model). We note that we have not changed the function
# documentation comments throughout the development process to ensure full visibility as to the
# information provided to the GenAI for implementation; and that the AI was instructucted to not
# add any comments to the implementations, to enable us to perform this process and check over the AI generated code.


# General guidance provided to the AI for all function implementation was as follows:
# 1. All code should be testable.
# 2. All code should handle errors gracefully to prevent crashes.
# 3. All code should be efficient, and concise as possible.
# 4. All code should use the logger to print helpful log messsages that can be used in any debugging.
# 5. Any added code should not be commented. (To allow for us to add comments ourselves).


class Crawler:
    def __init__(self, seeds, logger, indexer=None, politeness_window=6, crawl_limit=1000):
        # The Frontier will be a Python dictionary of host dictionaries.
        # Each host will be of the following form {"queue": deque(), "lastAccessed": datetime}.
        # The queue of each host will list all URL's that need crawling on that host.
        # The last accessed time of each host will store the time that a page was last downloaded/crawled from that host.
        self.frontier = {}

        # Maintain a set of seen URLs to prevent re-adding the same URL to the frontier during an execution.
        # A set is used for efficient retrieval.
        self.seen_urls = set()

        # Maintain a set of hosts disallowed by robots.txt to avoid repeated robots.txt checks.
        self.disallowed_hosts = set()

        # The politeness window enforces a delay between requests to the same host.
        self.politeness_window = politeness_window
        self.crawl_limit = crawl_limit
        self.request_timeout = 10

        # Keep track of the number of pages (successfully crawled).
        self.pages_crawled = 0

        # Used to log to the console for easier debugging.
        self.logger = logger

        # Indexer.
        self.indexer = indexer or Indexer(logger=logger)

        # Add all seed URLs to the frontier.
        for seed in seeds:
            self.add_url_to_frontier(seed)

    # ---------------------- Public Functions ----------------------

    def crawl(self):
        """ This function begins the crawling process. It continously scans the frontier for hosts that can be crawled, and 
            makes use of the download_web_page and parse_web_page functions to perform the crawl. It ensures that concurrent 
            requests to the same host are spaced by the politeness_window; and that we don't crawl any more pages than the crawl_limit.
        """

        # Record the start time of the crawl.
        crawl_start_time = datetime.now()

        # Continue crawling while the number of pages crawled is below the crawl limit.
        while self.pages_crawled < self.crawl_limit:
            crawled_this_scan = False
            shortest_wait = None

            # Iterate through every host in the frontier.
            for hostname, host in list(self.frontier.items()):

                # Check that the crawl limit has not been exceeded.
                if self.pages_crawled >= self.crawl_limit:
                    break

                # Ensure that the host has a queue.
                if not host["queue"]:
                    continue

                # Check when the host was last accessed by the crawler.
                now = datetime.now()
                last_accessed = host.get("last_accessed")
                # If the host has been accessed before:
                if last_accessed is not None:
                    # Use the politeness window to calculate when the host can next be accessed.
                    next_allowed = last_accessed + \
                        timedelta(seconds=self.politeness_window)
                    # If still within the politeness window, set a wait time for the next iteration.
                    if now < next_allowed:
                        wait_time = (next_allowed - now).total_seconds()
                        shortest_wait = wait_time if shortest_wait is None else min(
                            shortest_wait, wait_time)
                        continue

                # Crawl the web page.
                self.logger.info(f"Crawling host: {hostname}")
                web_page = self.download_web_page(host)
                crawled_this_scan = True

                # If the web page was crawled successfully, increment the page count.
                if web_page is not None:
                    self.parse_web_page(web_page)
                    self.pages_crawled += 1

            # Frontier is empty. Log a message and break the loop.
            if not any(host["queue"] for host in self.frontier.values()):
                self.logger.info("Crawler frontier is empty. Crawl complete.")
                break

            # If nothing was crawled in this scan, wait briefly to avoid busy idling.
            if not crawled_this_scan:
                sleep(max(0.1, shortest_wait or 0.1))

        # Log the total number of pages crawled during execution.
        print(f"Crawl complete. Pages crawled: {self.pages_crawled}")

        # Record the end time of the crawl.
        crawl_end_time = datetime.now()

        # Calculate the total time for the crawl and log it.
        total_crawl_time = (crawl_end_time-crawl_start_time).total_seconds()

        # Log the total crawling time
        print(f"Total crawl time = {total_crawl_time:.2f} seconds")

        # Save the index once the crawl is complete.
        self.indexer.save_index()

    # --------------------- Private Functions ----------------------

    def download_web_page(self, host):
        """ This function takes a host dictionary from the frontier, and pops the first web page from the host's queue before
            downloading it. It uses the requests library to download the web page. On download, the last_accessed time of the 
            host is updated to reflect the latest download.

            Args:
                host (dict): The downloaded web page to parse.
            Returns:
                requests.Response: The downloaded web page.
        """

        # Ensure that the host object and its queue are valid.
        if host is None or not host.get("queue"):
            self.logger.warning("No URL available to download for host.")
            return None

        # Pop the first URL from the host queue.
        url = host["queue"].popleft()

        try:
            self.logger.info(f"Downloading URL: {url}")
            # Attempt to download the page. We identify ourselves as a crawler.
            response = requests.get(url, timeout=self.request_timeout, headers={
                                    "User-Agent": "COMP3011Crawler/1.0"})
            host["last_accessed"] = datetime.now()
            # Raise an error on a failed download so control passes to the exception handler.
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            host["last_accessed"] = datetime.now()
            self.logger.warning(f"Failed to download URL {url}: {error}")
            return None

    def parse_web_page(self, web_page):
        """ This function parses a web page's HTML using the BeautifulSoup library. It makes use of the 
            add_url_to_frontier function to add any parsed links to the frontier.

            Args:
                web_page (requests.Response): The downloaded web page to parse.
        """

        # Check that web_page is not None.
        if web_page is None:
            self.logger.warning("No web page supplied for parsing.")
            return

        # Check that the web page has an HTML content type.
        content_type = web_page.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            self.logger.info(f"Skipping non-HTML content: {web_page.url}")
            return

        try:
            # Parse the page and extract links.
            soup = BeautifulSoup(web_page.text, "html.parser")
            links_added = 0

            for link in soup.find_all("a", href=True):
                # Resolve the link against the current web page URL.
                absolute_url = urljoin(web_page.url, link["href"])
                before_count = len(self.seen_urls)
                self.add_url_to_frontier(absolute_url)
                if len(self.seen_urls) > before_count:
                    links_added += 1

            self.logger.info(
                f"Parsed {web_page.url}; added {links_added} link(s) to frontier.")

            # Pass the page to the Indexer to be indexed.
            self.indexer.index_page(web_page.url, soup)
        except Exception as error:
            self.logger.warning(
                f"Failed to parse web page {getattr(web_page, 'url', 'unknown')}: {error}")

    def add_url_to_frontier(self, url):
        """ This function attempts to add a URL to the crawler frontier. Before doing so, it validates the URL using 
            the validators library and ensures that the URL isn't in the seen_urls set. If the URL is valid, then
            it adds the URL to the corresponding host queue (if the host already exists in the frontier); or uses
            the add_host_to_frontier function to attempt to add the host to the frontier. In the scenario that the URL
            is successfully added to the frontier, the URL should be added to the seen_urls set. 

            Args:
                url (str): The URL to add to the frontier.
        """
        if not url:
            return

        try:
            parsed_url = urlparse(url)
            # Remove fragments from the URL, as they still refer to the same page.
            cleaned_url = parsed_url._replace(fragment="").geturl()
            hostname = parsed_url.hostname

            # Ensure that this URL has not already been seen.
            if cleaned_url in self.seen_urls:
                return

            # Ensure that the URL is valid.
            if not validators.url(cleaned_url) or hostname is None:
                self.logger.warning(
                    f"Invalid URL not added to frontier: {url}")
                return

            # Check whether the host has already been marked as disallowed.
            if hostname in self.disallowed_hosts:
                return

            # Attempt to add the host to the frontier.
            if hostname not in self.frontier and not self.add_host_to_frontier(hostname):
                self.logger.info(f"Host not added to frontier: {hostname}")
                return

            self.frontier[hostname]["queue"].append(cleaned_url)
            # Add the URL to the seen set to prevent it from being added to the frontier again during this execution.
            self.seen_urls.add(cleaned_url)
            self.logger.info(f"Added URL to frontier: {cleaned_url}")
        except Exception as error:
            self.logger.warning(
                f"Failed to add URL to frontier {url}: {error}")

    def add_host_to_frontier(self, hostname):
        """ This function attempts to add a host object to the crawler frontier. Before adding the host object to the frontier,
            it checks the robots.txt file of the host to ensure crawling is allowed. If it is not allowed, then the host
            object will not be added to the frontier.

            Args:
                hostname (str): The name of the host to add to the frontier.
            Returns:
                bool: True if the host was added. False otherwise.
        """

        if hostname is not None and hostname not in self.frontier:
            try:
                # Request the robots.txt file from the host.
                robots_url = f"https://{hostname}/robots.txt"
                robots_response = requests.get(
                    robots_url,
                    timeout=self.request_timeout,
                    headers={"User-Agent": "COMP3011Crawler/1.0"},
                )
                robots_response.raise_for_status()

                # Parse the robots.txt file.
                robots_parser = RobotFileParser()
                robots_parser.set_url(robots_url)
                robots_parser.parse(robots_response.text.splitlines())

                # Check that this crawler is allowed to fetch the web page.
                if not robots_parser.can_fetch("COMP3011Crawler/1.0", f"https://{hostname}/"):
                    # If not, cache the host as disallowed to avoid refetching robots.txt.
                    self.disallowed_hosts.add(hostname)
                    self.logger.info(
                        f"Crawling disallowed by robots.txt for host: {hostname}")
                    return False
            except requests.RequestException as error:
                self.logger.warning(
                    f"Could not read robots.txt for {hostname}; allowing host: {error}")

            # Use collections.deque for more efficient FIFO queue operations.
            self.frontier[hostname] = {"queue": deque(), "last_accessed": None}
            self.logger.info(f"Added host to frontier: {hostname}")
            return True

        return False
