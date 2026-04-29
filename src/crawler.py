from collections import deque

# To implement the crawler functionality, we used the lecture slides to write function stubs and
# detailed descriptions for implementation by a GenAI tool. The GenAI tool used to generate the
# implementations was ChatGPT (5.2 Thinking model). We note that we have not changed the function
# documentation comments throughout the development process to ensure full visibility as to the
# information provided to the GenAI for implementation.


# General guidance provided to the AI for all function implementation was as follows:
# 1. All code should be testable.
# 2. All code should handle errors gracefully to prevent crashes.
# 3. All code should be efficient, and concise as possible.
# 4. All code should be thread-safe to enable multithreaded execution.
# 5. All code should use the logger to print helpful log messsages that can be used in any debugging.


class Crawler:
    def __init__(self, seeds, logger, politeness_window=6, crawl_limit=1000):
        # The Frontier will be a Python dictionary of host dictionaries.
        # Each host will be of the following form {"queue": deque(), "lastAccessed": datetime}.
        # The queue of each host will list all URL's that need crawling on that host.
        # The last accessed time of each host will store the time that a page was last downloaded/crawled from that host.
        self.frontier = {}

        # Maintain a set of crawled URLs to prevent re-crawling the same URL during an execution.
        self.crawled_urls = set()

        # Politeness window enforces a time between concurrent requests to a host.
        self.politeness_window = politeness_window
        self.crawl_limit = crawl_limit

        # Keep track of the number of pages (successfully crawled).
        self.pages_crawled = 0

        # Used to log into the console for easier debugging.
        self.logger = logger

        # Add all seeds used to the frontier.
        for seed in seeds:
            self.add_url_to_frontier(seed)

    def crawl():
        """ This function begins the crawling process. It continously scans the frontier for hosts that can be crawled, and 
            makes use of the download_web_page and parse_web_page functions to perform the crawl. It ensures that concurrent 
            requests to the same host are spaced by the politeness_window; and that we don't crawl any more pages than the crawl_limit.
            It uses the concurrent.futures library to spawn a thread group to speed up the crawling process.
        """

    def download_web_page(self, host):
        """ This function takes a host dictionary from the frontier, and pops the first web page from the host's queue before
            downloading it. It uses the requests library to download the web page. On download, the last_accessed time of the 
            host is updated to reflect the latest download.

            Args:
                host (dict): The downloaded web page to parse.
            Returns:
                requests.Response: The downloaded web page.
        """

    def parse_web_page(self, web_page):
        """ This function parses a web page's HTML using the BeautifulSoup library. It makes use of the 
            add_url_to_frontier function to add any parsed links to the frontier.

            Args:
                web_page (requests.Response): The downloaded web page to parse.
        """

    def add_url_to_frontier(self, url):
        """ This function attempts to add a URL to the crawler frontier. Before doing so, it validates the URL using 
            the validators library and ensures that the URL isn't in the crawled_urls set. If the URL is valid, then
            it adds the URL to the corresponding host queue (if the host already exists in the frontier); or uses
            the add_host_to_frontier function to attempt to add the host to the frontier. In the scenario that the URL
            is successfully added to the frontier, the URL should be added to the crawled_urls set. 

            Args:
                url (str): The URL to add to the frontier.
        """

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
            # Queue defined as collections.deque for more efficient FIFO operations.
            self.frontier[hostname] = {"queue": deque(), "last_accessed": None}
