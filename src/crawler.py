from collections import deque
from datetime import datetime, timedelta
from time import sleep
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
import validators
from bs4 import BeautifulSoup

# To implement the crawler functionality, we used the lecture slides to write function stubs and
# detailed descriptions for implementation by a GenAI tool. The GenAI tool used to generate the
# implementations was ChatGPT (5.2 Thinking model). We note that we have not changed the function
# documentation comments throughout the development process to ensure full visibility as to the
# information provided to the GenAI for implementation. We note that the AI was instructucted to not
# add any comments to the implementations, to enable us to perform this process and check over the AI generated code.


# General guidance provided to the AI for all function implementation was as follows:
# 1. All code should be testable.
# 2. All code should handle errors gracefully to prevent crashes.
# 3. All code should be efficient, and concise as possible.
# 4. All code should use the logger to print helpful log messsages that can be used in any debugging.
# 5. Do not add any comments to the function.


class Crawler:
    def __init__(self, seeds, logger, politeness_window=6, crawl_limit=1000):
        # The Frontier will be a Python dictionary of host dictionaries.
        # Each host will be of the following form {"queue": deque(), "lastAccessed": datetime}.
        # The queue of each host will list all URL's that need crawling on that host.
        # The last accessed time of each host will store the time that a page was last downloaded/crawled from that host.
        self.frontier = {}

        # Maintain a set of crawled URLs to prevent re-crawling the same URL during an execution.
        # A set is used for efficient retrieval.
        self.crawled_urls = set()

        # Maintain a set of hosts disallowed by robots.txt to avoid repeated robots.txt checks.
        self.disallowed_hosts = set()

        # Politeness window enforces a time between concurrent requests to a host.
        self.politeness_window = politeness_window
        self.crawl_limit = crawl_limit
        self.request_timeout = 10

        # Keep track of the number of pages (successfully crawled).
        self.pages_crawled = 0

        # Used to log into the console for easier debugging.
        self.logger = logger

        # Add all seeds used to the frontier.
        for seed in seeds:
            self.add_url_to_frontier(seed)

    def crawl(self):
        """ This function begins the crawling process. It continously scans the frontier for hosts that can be crawled, and 
            makes use of the download_web_page and parse_web_page functions to perform the crawl. It ensures that concurrent 
            requests to the same host are spaced by the politeness_window; and that we don't crawl any more pages than the crawl_limit.
        """
        while self.pages_crawled < self.crawl_limit:
            crawled_this_scan = False
            shortest_wait = None

            for hostname, host in list(self.frontier.items()):
                if self.pages_crawled >= self.crawl_limit:
                    break

                if not host["queue"]:
                    continue

                now = datetime.now()
                last_accessed = host.get("last_accessed")
                if last_accessed is not None:
                    next_allowed = last_accessed + timedelta(seconds=self.politeness_window)
                    if now < next_allowed:
                        wait_time = (next_allowed - now).total_seconds()
                        shortest_wait = wait_time if shortest_wait is None else min(shortest_wait, wait_time)
                        continue

                self.logger.info(f"Crawling host: {hostname}")
                web_page = self.download_web_page(host)
                crawled_this_scan = True

                if web_page is not None:
                    self.pages_crawled += 1
                    self.parse_web_page(web_page)

            if not any(host["queue"] for host in self.frontier.values()):
                self.logger.info("Crawler frontier is empty. Crawl complete.")
                break

            if not crawled_this_scan:
                sleep(max(0.1, shortest_wait or 0.1))

        self.logger.info(f"Crawl complete. Pages crawled: {self.pages_crawled}")

    def download_web_page(self, host):
        """ This function takes a host dictionary from the frontier, and pops the first web page from the host's queue before
            downloading it. It uses the requests library to download the web page. On download, the last_accessed time of the 
            host is updated to reflect the latest download.

            Args:
                host (dict): The downloaded web page to parse.
            Returns:
                requests.Response: The downloaded web page.
        """
        if host is None or not host.get("queue"):
            self.logger.warning("No URL available to download for host.")
            return None

        url = host["queue"].popleft()

        try:
            self.logger.info(f"Downloading URL: {url}")
            response = requests.get(url, timeout=self.request_timeout, headers={"User-Agent": "COMP3011Crawler/1.0"})
            host["last_accessed"] = datetime.now()
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
        if web_page is None:
            self.logger.warning("No web page supplied for parsing.")
            return

        content_type = web_page.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            self.logger.info(f"Skipping non-HTML content: {web_page.url}")
            return

        try:
            soup = BeautifulSoup(web_page.text, "html.parser")
            links_added = 0

            for link in soup.find_all("a", href=True):
                absolute_url = urljoin(web_page.url, link["href"])
                before_count = len(self.crawled_urls)
                self.add_url_to_frontier(absolute_url)
                if len(self.crawled_urls) > before_count:
                    links_added += 1

            self.logger.info(f"Parsed {web_page.url}; added {links_added} link(s) to frontier.")
        except Exception as error:
            self.logger.warning(f"Failed to parse web page {getattr(web_page, 'url', 'unknown')}: {error}")

    def add_url_to_frontier(self, url):
        """ This function attempts to add a URL to the crawler frontier. Before doing so, it validates the URL using 
            the validators library and ensures that the URL isn't in the crawled_urls set. If the URL is valid, then
            it adds the URL to the corresponding host queue (if the host already exists in the frontier); or uses
            the add_host_to_frontier function to attempt to add the host to the frontier. In the scenario that the URL
            is successfully added to the frontier, the URL should be added to the crawled_urls set. 

            Args:
                url (str): The URL to add to the frontier.
        """
        if not url:
            return

        try:
            parsed_url = urlparse(url)
            cleaned_url = parsed_url._replace(fragment="").geturl()
            hostname = parsed_url.hostname

            if cleaned_url in self.crawled_urls:
                return

            if not validators.url(cleaned_url) or hostname is None:
                self.logger.warning(f"Invalid URL not added to frontier: {url}")
                return

            if hostname in self.disallowed_hosts:
                return

            if hostname not in self.frontier and not self.add_host_to_frontier(hostname):
                self.logger.info(f"Host not added to frontier: {hostname}")
                return

            self.frontier[hostname]["queue"].append(cleaned_url)
            self.crawled_urls.add(cleaned_url)
            self.logger.info(f"Added URL to frontier: {cleaned_url}")
        except Exception as error:
            self.logger.warning(f"Failed to add URL to frontier {url}: {error}")

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
                robots_url = f"https://{hostname}/robots.txt"
                robots_response = requests.get(
                    robots_url,
                    timeout=self.request_timeout,
                    headers={"User-Agent": "COMP3011Crawler/1.0"},
                )
                robots_response.raise_for_status()

                robots_parser = RobotFileParser()
                robots_parser.set_url(robots_url)
                robots_parser.parse(robots_response.text.splitlines())

                if not robots_parser.can_fetch("COMP3011Crawler/1.0", f"https://{hostname}/"):
                    self.disallowed_hosts.add(hostname)
                    self.logger.info(f"Crawling disallowed by robots.txt for host: {hostname}")
                    return False
            except requests.RequestException as error:
                self.logger.warning(f"Could not read robots.txt for {hostname}; allowing host: {error}")

            # Queue defined as collections.deque for more efficient FIFO operations.
            self.frontier[hostname] = {"queue": deque(), "last_accessed": None}
            self.logger.info(f"Added host to frontier: {hostname}")
            return True

        return False
