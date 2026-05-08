""" --------------------------- GEN AI USAGE DECLARATION ----------------------------
    Disclaimer: All test code in this file was generated entirely by ChatGPT
    (5.5 thinking model).

    ChatGPT was given the context of the implemented crawler.py file, and given
    the following prompt:
    - "Imagine you are an experienced software developer that has been tasked
       with implementing a crawler for an upcoming search engine company. The
       crawler code provided has been implemented by your team; and now you
       have been tasked to write a high-coverage (>90%) test file for the
       implementation. You have been given instructions by the team to ensure
       all edge and boundary cases are covered, and that the tests are written
       as concisely, efficiently and as readable as possible."

    NOTE: To demonstrate our understanding of all the code written, we wrote
    all comments and documentation comments ourselves. The GenAI did not create
    any comments. We did, however, ask the GenAI to check and make changes for
    ONLY spelling/grammar/styling mistakes.
    ------------------------- GEN AI USAGE DECLARATION END --------------------------
"""

from collections import deque
from datetime import datetime
from unittest.mock import Mock
import pytest
import requests
import sys
from pathlib import Path

# Since the crawler is not currently packaged, we need to resolve it from the parent directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from crawler import Crawler


class DummyLogger:
    """A mock logger."""

    def __init__(self):
        self.info = Mock()
        self.warning = Mock()


class FakeResponse:
    """A mock response object."""

    def __init__(self, url="https://example.com/", text="", content_type="text/html", error=None):
        self.url = url
        self.text = text
        self.headers = {"Content-Type": content_type}
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error


@pytest.fixture
def logger():
    return DummyLogger()


@pytest.fixture
def crawler(logger):
    return Crawler([], logger, politeness_window=1, crawl_limit=10)


def robots_response(text="User-agent: *\nAllow: /", error=None):
    """Build and return a mock response for a robots.txt request.

        Args:
            text (str, optional): The mock response returned when requesting the robots.txt
                file from the host.
            error (any, optional): An error raised when requesting the robots.txt file.
        Returns:
            FakeResponse: A mocked robots.txt response object from a host.
    """
    return FakeResponse(url="https://example.com/robots.txt", text=text, error=error)


def test_init_adds_each_seed_through_frontier(monkeypatch, logger):
    """Ensure that the constructor adds each seed through the frontier logic.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            logger (logger): A mock logger object.
    """

    added = []

    # Replace add_url_to_frontier so it adds URLs to the test list.
    monkeypatch.setattr(Crawler, "add_url_to_frontier",
                        lambda self, url: added.append(url))

    # Initialise the crawler with seeds.
    crawler = Crawler(["https://a.test", "https://b.test"], logger)

    # Assert that the seeds were added to the test list.
    assert crawler.frontier == {}
    assert crawler.seen_urls == set()
    assert crawler.disallowed_hosts == set()
    assert crawler.allowed_hosts == set()
    assert crawler.single_host is False
    assert crawler.pages_crawled == 0
    assert added == ["https://a.test", "https://b.test"]


def test_init_sets_allowed_hosts_in_single_host_mode(monkeypatch, logger):
    """Ensure that single_host mode restricts crawling to the seed hosts.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            logger (logger): A mock logger object.
    """

    monkeypatch.setattr(Crawler, "add_url_to_frontier", lambda self, url: None)

    crawler = Crawler(["https://a.test", "https://b.test"], logger, single_host=True)

    assert crawler.allowed_hosts == {"a.test", "b.test"}
    assert crawler.single_host is True


def test_add_host_allows_when_robots_allows(monkeypatch, crawler):
    """Ensure that the crawler adds a host to the frontier when robots.txt permits crawling.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Mock a robots.txt response that permits crawling.
    get = Mock(return_value=robots_response("User-agent: *\nAllow: /"))
    monkeypatch.setattr("crawler.requests.get", get)

    # Assert that the crawler adds the host, using the mocked robots.txt file, to the frontier.
    assert crawler.add_host_to_frontier("example.com") is True
    assert crawler.frontier["example.com"]["queue"] == deque()
    assert crawler.frontier["example.com"]["last_accessed"] is None
    get.assert_called_once_with(
        "https://example.com/robots.txt",
        timeout=crawler.request_timeout,
        headers={"User-Agent": "COMP3011Crawler/1.0"},
    )


def test_add_host_disallows_when_robots_blocks(monkeypatch, crawler):
    """Ensure that the crawler does not add a host to the frontier when robots.txt blocks crawling.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Mock a robots.txt response that prohibits crawling.
    monkeypatch.setattr("crawler.requests.get", Mock(
        return_value=robots_response("User-agent: *\nDisallow: /")))

    # Assert that the host, using the mocked robots.txt file, is not added to the crawler frontier.
    assert crawler.add_host_to_frontier("example.com") is False
    assert "example.com" not in crawler.frontier
    assert "example.com" in crawler.disallowed_hosts


def test_add_host_allows_when_robots_unavailable(monkeypatch, crawler):
    """Ensure that the crawler adds a host to the frontier when robots.txt is unavailable.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Mock an error while retrieving the robots.txt file from the host.
    error = requests.RequestException("robots unavailable")
    monkeypatch.setattr("crawler.requests.get", Mock(
        return_value=robots_response(error=error)))

    # Assert that the host is added to the frontier.
    assert crawler.add_host_to_frontier("example.com") is True
    assert "example.com" in crawler.frontier
    crawler.logger.warning.assert_called()


def test_add_host_returns_false_for_none_or_existing(crawler):
    """Ensure that add_host_to_frontier returns False for None or an existing host.

        Args:
            crawler (Crawler): The instantiated Crawler object.
    """

    # Mock a host in the frontier.
    crawler.frontier["example.com"] = {"queue": deque(), "last_accessed": None}

    # Assert that the host is not added to the frontier.
    assert crawler.add_host_to_frontier(None) is False
    assert crawler.add_host_to_frontier("example.com") is False


def test_add_url_adds_cleaned_url_to_existing_host(monkeypatch, crawler):
    """Ensure that the crawler adds a cleaned URL to the queue of an existing host.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Mock an existing host on the frontier.
    crawler.frontier["example.com"] = {"queue": deque(), "last_accessed": None}
    # Mock the URL validator to return True.
    monkeypatch.setattr("crawler.validators.url", Mock(return_value=True))

    # Call the function to add the URL to the frontier.
    crawler.add_url_to_frontier("https://example.com/path#section")

    # Assert that the URL is added to the host queue and to the seen_urls set.
    assert list(crawler.frontier["example.com"]["queue"]) == [
        "https://example.com/path"]
    assert "https://example.com/path" in crawler.seen_urls


def test_add_url_rejects_empty_duplicate_invalid_and_disallowed(monkeypatch, crawler):
    """Ensure that the crawler does not add empty, invalid, duplicate, or disallowed URLs to the frontier.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    crawler.frontier["example.com"] = {"queue": deque(), "last_accessed": None}
    crawler.seen_urls.add("https://example.com/seen")
    crawler.disallowed_hosts.add("blocked.test")
    validate = Mock(side_effect=lambda value: value != "not a url")
    monkeypatch.setattr("crawler.validators.url", validate)

    # Call the function with invalid arguments.
    crawler.add_url_to_frontier("")
    crawler.add_url_to_frontier("https://example.com/seen")
    crawler.add_url_to_frontier("not a url")
    crawler.add_url_to_frontier("https://blocked.test/page")

    # Assert that none of the URLs were added to the frontier and that the logger recorded the error.
    assert list(crawler.frontier["example.com"]["queue"]) == []
    crawler.logger.warning.assert_any_call(
        "Invalid URL not added to frontier: not a url")


def test_add_url_rejects_out_of_scope_host(monkeypatch, crawler):
    """Ensure that the crawler only queues URLs on the seed host.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    crawler.allowed_hosts = {"example.com"}
    monkeypatch.setattr("crawler.validators.url", Mock(return_value=True))

    crawler.add_url_to_frontier("https://other.example/page")

    assert "other.example" not in crawler.frontier
    assert "https://other.example/page" not in crawler.seen_urls


def test_add_url_rejects_url_blocked_by_robots(monkeypatch, crawler):
    """Ensure that the crawler checks robots.txt against the concrete URL being queued.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    crawler.frontier["example.com"] = {"queue": deque(), "last_accessed": None}
    crawler.allowed_hosts = {"example.com"}
    monkeypatch.setattr("crawler.validators.url", Mock(return_value=True))

    class FakeRobotsParser:
        def can_fetch(self, _agent, url):
            return not url.endswith("/blocked")

    crawler.robots_parsers["example.com"] = FakeRobotsParser()

    crawler.add_url_to_frontier("https://example.com/blocked")

    assert list(crawler.frontier["example.com"]["queue"]) == []
    assert "https://example.com/blocked" not in crawler.seen_urls


def test_parse_web_page_follows_links_when_present(logger):
    """Ensure that parsing a page still follows discovered links.

        Args:
            logger (logger): A mock logger object.
    """

    indexer = Mock()
    crawler = Crawler([], logger, indexer=indexer)
    crawler.add_url_to_frontier = Mock()
    response = FakeResponse(
        url="https://example.com/",
        text='<html><body><a href="/next">Next</a><p>Body</p></body></html>',
    )

    crawler.parse_web_page(response)

    crawler.add_url_to_frontier.assert_called_once_with("https://example.com/next")
    indexer.index_page.assert_called_once()


def test_add_url_adds_new_host_and_handles_host_rejection(monkeypatch, crawler):
    """Ensure that the crawler adds new hosts through add_url_to_frontier and handles host rejection cleanly.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    monkeypatch.setattr("crawler.validators.url", Mock(return_value=True))
    add_host = Mock(side_effect=[False, True])
    monkeypatch.setattr(crawler, "add_host_to_frontier", add_host)

    # Ensure that the host was not added to the crawled URLs.
    crawler.add_url_to_frontier("https://blocked.example/page")
    assert "https://blocked.example/page" not in crawler.seen_urls

    # Setup mocks.
    def add_real_host(hostname):
        crawler.frontier[hostname] = {"queue": deque(), "last_accessed": None}
        return True
    add_host.side_effect = add_real_host

    # Ensure that the host was added to the frontier and that the page was added to the crawled URLs.
    crawler.add_url_to_frontier("https://new.example/page")
    assert list(crawler.frontier["new.example"]["queue"]) == [
        "https://new.example/page"]
    assert "https://new.example/page" in crawler.seen_urls


def test_add_url_logs_unexpected_errors(monkeypatch, crawler):
    """Ensure that the crawler logs unexpected errors while adding a URL to the frontier.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks and call the function.
    monkeypatch.setattr("crawler.urlparse", Mock(
        side_effect=ValueError("bad parse")))
    crawler.add_url_to_frontier("https://example.com")

    # Assert that the unexpected error was logged as a warning and that the URL was not added to the frontier.
    crawler.logger.warning.assert_called()
    assert crawler.frontier == {}


def test_download_web_page_returns_none_without_url(crawler):
    """Ensure that download_web_page returns None when no valid URL input is supplied.

        Args:
            crawler (Crawler): The instantiated Crawler object.
    """

    # Assert that download_web_page returns None and that the logger recorded two warnings.
    assert crawler.download_web_page(None) is None
    assert crawler.download_web_page(
        {"queue": deque(), "last_accessed": None}) is None
    assert crawler.logger.warning.call_count == 2


def test_download_web_page_success_updates_last_accessed(monkeypatch, crawler):
    """Ensure that a successful download updates the host's last_accessed time in the frontier.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    response = FakeResponse(url="https://example.com/page", text="ok")
    get = Mock(return_value=response)
    host = {"queue": deque(["https://example.com/page"]),
            "last_accessed": None}
    monkeypatch.setattr("crawler.requests.get", get)

    # Assert that the last_accessed time is updated.
    assert crawler.download_web_page(host) is response
    assert host["queue"] == deque()
    assert isinstance(host["last_accessed"], datetime)
    get.assert_called_once_with(
        "https://example.com/page",
        timeout=crawler.request_timeout,
        headers={"User-Agent": "COMP3011Crawler/1.0"},
    )


def test_download_web_page_failure_updates_last_accessed_and_logs(monkeypatch, crawler):
    """Ensure that a failed download still updates last_accessed and logs the error.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    error = requests.RequestException("boom")
    host = {"queue": deque(["https://example.com/missing"]),
            "last_accessed": None}
    monkeypatch.setattr("crawler.requests.get", Mock(side_effect=error))

    # Assert that last_accessed was updated and that the logger recorded a warning.
    assert crawler.download_web_page(host) is None
    assert isinstance(host["last_accessed"], datetime)
    crawler.logger.warning.assert_called()


def test_parse_web_page_handles_none_and_non_html(crawler):
    """Ensure that parse_web_page handles None and non-HTML content gracefully.

        Args:
            crawler (Crawler): The instantiated Crawler object.
    """

    # Call parse_web_page with invalid inputs.
    crawler.parse_web_page(None)
    crawler.parse_web_page(FakeResponse(
        url="https://example.com/file.pdf", content_type="application/pdf"))

    # Ensure that warnings were logged for these invalid arguments.
    crawler.logger.warning.assert_called_with(
        "No web page supplied for parsing.")
    crawler.logger.info.assert_any_call(
        "Skipping non-HTML content: https://example.com/file.pdf")


def test_parse_web_page_adds_absolute_relative_and_fragment_links(monkeypatch, crawler):
    """Ensure that the crawler adds relative, absolute, and fragment links to the frontier as separate paths.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Create a list to collect the URLs.
    added = []

    # Mock the add_url_to_frontier function.
    def record(url):
        added.append(url)
        crawler.seen_urls.add(url)
    monkeypatch.setattr(crawler, "add_url_to_frontier", record)

    # Mock an HTML response containing links.
    response = FakeResponse(
        url="https://example.com/base/index.html",
        text="""
        <html><body>
            <a href="/absolute">Absolute</a>
            <a href="relative">Relative</a>
            <a href="#local">Local fragment</a>
            <a>No href</a>
        </body></html>
        """,
        content_type="Text/HTML; charset=utf-8",
    )
    crawler.parse_web_page(response)

    # Assert that all links were added to the mocked frontier and that the crawler logged the additions.
    assert added == [
        "https://example.com/absolute",
        "https://example.com/base/relative",
        "https://example.com/base/index.html#local",
    ]
    crawler.logger.info.assert_any_call(
        "Parsed https://example.com/base/index.html; added 3 link(s) to frontier.")


def test_parse_web_page_catches_parser_errors(monkeypatch, crawler):
    """Ensure that the crawler handles errors encountered while parsing a web page for links.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    monkeypatch.setattr("crawler.BeautifulSoup", Mock(
        side_effect=RuntimeError("bad html")))

    # Call the function and assert that the error was caught and logged.
    crawler.parse_web_page(FakeResponse(
        url="https://example.com/broken", text="<html>"))
    crawler.logger.warning.assert_called()


def test_crawl_downloads_parses_and_stops_when_frontier_empty(monkeypatch, crawler):
    """Ensure that the crawler stops when no URLs remain in the frontier.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    response = FakeResponse(
        url="https://example.com/page", text="<html></html>")
    crawler.frontier["example.com"] = {"queue": deque(
        ["https://example.com/page"]), "last_accessed": None}

    def download_once(host):
        host["queue"].popleft()
        return response

    download = Mock(side_effect=download_once)
    parse = Mock()
    monkeypatch.setattr(crawler, "download_web_page", download)
    monkeypatch.setattr(crawler, "parse_web_page", parse)

    # Start the crawl and ensure that the crawler terminates.
    crawler.crawl()
    assert crawler.pages_crawled == 1
    download.assert_called_once_with(crawler.frontier["example.com"])
    parse.assert_called_once_with(response)


def test_crawl_respects_crawl_limit(monkeypatch, crawler):
    """Ensure that the crawler respects the crawl limit.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    crawler.crawl_limit = 1
    crawler.frontier["example.com"] = {"queue": deque(
        ["https://example.com/1", "https://example.com/2"]), "last_accessed": None}
    monkeypatch.setattr(crawler, "download_web_page",
                        Mock(return_value=FakeResponse()))
    monkeypatch.setattr(crawler, "parse_web_page", Mock())

    # Start the crawl and assert that it stops upon reaching the crawl limit.
    crawler.crawl()
    assert crawler.pages_crawled == 1
    assert len(crawler.frontier["example.com"]["queue"]) == 2


def test_crawl_does_not_count_failed_download(monkeypatch, crawler):
    """Ensure that failed downloads do not count toward the crawl limit.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    crawler.frontier["example.com"] = {"queue": deque(
        ["https://example.com/fail"]), "last_accessed": None}

    def fail_download(host):
        host["queue"].popleft()
        return None
    monkeypatch.setattr(crawler, "download_web_page",
                        Mock(side_effect=fail_download))
    parse = Mock()
    monkeypatch.setattr(crawler, "parse_web_page", parse)

    # Start the crawl and assert that pages_crawled was not incremented by the failed download.
    crawler.crawl()
    assert crawler.pages_crawled == 0
    parse.assert_not_called()


def test_crawl_waits_when_all_hosts_are_inside_politeness_window(monkeypatch, crawler):
    """Ensure that the crawler waits when all hosts in the frontier are within their politeness window.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Set up the mocks.
    host = {"queue": deque(["https://example.com/later"]),
            "last_accessed": datetime.now()}
    crawler.frontier["example.com"] = host
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)
        host["queue"].clear()
    monkeypatch.setattr("crawler.sleep", fake_sleep)

    # Start the crawl and assert that the crawler waits rather than performing any crawling.
    crawler.crawl()
    assert slept and slept[0] >= 0.1
    assert crawler.pages_crawled == 0


def test_crawl_empty_frontier_finishes_without_download(monkeypatch, crawler):
    """Ensure that the crawler does not attempt any downloads when the frontier is empty.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            crawler (Crawler): The instantiated Crawler object.
    """

    # Setup mocks.
    download = Mock()
    monkeypatch.setattr(crawler, "download_web_page", download)

    # Start the crawl and assert that no download was attempted and that the crawler logged its completion.
    crawler.crawl()
    download.assert_not_called()
    crawler.logger.info.assert_any_call(
        "Crawler frontier is empty. Crawl complete.")
