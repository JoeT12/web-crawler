""" Disclaimer: All test code in this file was generated entirely by ChatGPT (5.5 thinking model).
    
    ChatGPT was given the context of the implemented crawler.py file, and given 
    the following prompt
    - "Imagine you are an experienced software developer that has been tasked with implementing a 
       crawler for an upcoming search engine company. The crawler code provided has been implemented by your team; 
       and now you have been tasked to write a high-coverage (>90%) test file for the implementation. 
       You have been given instructions by the team to ensure all edge and boundary cases are covered, and that 
       the tests are written as concisely, efficiently and as readable as possible."
"""

from collections import deque
from datetime import datetime
from unittest.mock import Mock

import pytest
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from crawler import Crawler


class DummyLogger:
    def __init__(self):
        self.info = Mock()
        self.warning = Mock()


class FakeResponse:
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
    return FakeResponse(url="https://example.com/robots.txt", text=text, error=error)


def test_init_adds_each_seed_through_frontier(monkeypatch, logger):
    added = []
    monkeypatch.setattr(Crawler, "add_url_to_frontier", lambda self, url: added.append(url))

    crawler = Crawler(["https://a.test", "https://b.test"], logger)

    assert crawler.frontier == {}
    assert crawler.crawled_urls == set()
    assert crawler.disallowed_hosts == set()
    assert crawler.pages_crawled == 0
    assert added == ["https://a.test", "https://b.test"]


def test_add_host_allows_when_robots_allows(monkeypatch, crawler):
    get = Mock(return_value=robots_response("User-agent: *\nAllow: /"))
    monkeypatch.setattr("crawler.requests.get", get)

    assert crawler.add_host_to_frontier("example.com") is True
    assert crawler.frontier["example.com"]["queue"] == deque()
    assert crawler.frontier["example.com"]["last_accessed"] is None
    get.assert_called_once_with(
        "https://example.com/robots.txt",
        timeout=crawler.request_timeout,
        headers={"User-Agent": "COMP3011Crawler/1.0"},
    )


def test_add_host_disallows_when_robots_blocks(monkeypatch, crawler):
    monkeypatch.setattr("crawler.requests.get", Mock(return_value=robots_response("User-agent: *\nDisallow: /")))

    assert crawler.add_host_to_frontier("example.com") is False
    assert "example.com" not in crawler.frontier
    assert "example.com" in crawler.disallowed_hosts


def test_add_host_allows_when_robots_unavailable(monkeypatch, crawler):
    error = requests.RequestException("robots unavailable")
    monkeypatch.setattr("crawler.requests.get", Mock(return_value=robots_response(error=error)))

    assert crawler.add_host_to_frontier("example.com") is True
    assert "example.com" in crawler.frontier
    crawler.logger.warning.assert_called()


def test_add_host_returns_false_for_none_or_existing(crawler):
    crawler.frontier["example.com"] = {"queue": deque(), "last_accessed": None}

    assert crawler.add_host_to_frontier(None) is False
    assert crawler.add_host_to_frontier("example.com") is False


def test_add_url_adds_cleaned_url_to_existing_host(monkeypatch, crawler):
    crawler.frontier["example.com"] = {"queue": deque(), "last_accessed": None}
    monkeypatch.setattr("crawler.validators.url", Mock(return_value=True))

    crawler.add_url_to_frontier("https://example.com/path#section")

    assert list(crawler.frontier["example.com"]["queue"]) == ["https://example.com/path"]
    assert "https://example.com/path" in crawler.crawled_urls


def test_add_url_rejects_empty_duplicate_invalid_and_disallowed(monkeypatch, crawler):
    crawler.frontier["example.com"] = {"queue": deque(), "last_accessed": None}
    crawler.crawled_urls.add("https://example.com/seen")
    crawler.disallowed_hosts.add("blocked.test")
    validate = Mock(side_effect=lambda value: value != "not a url")
    monkeypatch.setattr("crawler.validators.url", validate)

    crawler.add_url_to_frontier("")
    crawler.add_url_to_frontier("https://example.com/seen")
    crawler.add_url_to_frontier("not a url")
    crawler.add_url_to_frontier("https://blocked.test/page")

    assert list(crawler.frontier["example.com"]["queue"]) == []
    crawler.logger.warning.assert_any_call("Invalid URL not added to frontier: not a url")


def test_add_url_adds_new_host_and_handles_host_rejection(monkeypatch, crawler):
    monkeypatch.setattr("crawler.validators.url", Mock(return_value=True))
    add_host = Mock(side_effect=[False, True])
    monkeypatch.setattr(crawler, "add_host_to_frontier", add_host)

    crawler.add_url_to_frontier("https://blocked.example/page")
    assert "https://blocked.example/page" not in crawler.crawled_urls

    def add_real_host(hostname):
        crawler.frontier[hostname] = {"queue": deque(), "last_accessed": None}
        return True

    add_host.side_effect = add_real_host
    crawler.add_url_to_frontier("https://new.example/page")

    assert list(crawler.frontier["new.example"]["queue"]) == ["https://new.example/page"]
    assert "https://new.example/page" in crawler.crawled_urls


def test_add_url_logs_unexpected_errors(monkeypatch, crawler):
    monkeypatch.setattr("crawler.urlparse", Mock(side_effect=ValueError("bad parse")))

    crawler.add_url_to_frontier("https://example.com")

    crawler.logger.warning.assert_called()
    assert crawler.frontier == {}


def test_download_web_page_returns_none_without_url(crawler):
    assert crawler.download_web_page(None) is None
    assert crawler.download_web_page({"queue": deque(), "last_accessed": None}) is None
    assert crawler.logger.warning.call_count == 2


def test_download_web_page_success_updates_last_accessed(monkeypatch, crawler):
    response = FakeResponse(url="https://example.com/page", text="ok")
    get = Mock(return_value=response)
    host = {"queue": deque(["https://example.com/page"]), "last_accessed": None}
    monkeypatch.setattr("crawler.requests.get", get)

    assert crawler.download_web_page(host) is response
    assert host["queue"] == deque()
    assert isinstance(host["last_accessed"], datetime)
    get.assert_called_once_with(
        "https://example.com/page",
        timeout=crawler.request_timeout,
        headers={"User-Agent": "COMP3011Crawler/1.0"},
    )


def test_download_web_page_failure_updates_last_accessed_and_logs(monkeypatch, crawler):
    error = requests.RequestException("boom")
    host = {"queue": deque(["https://example.com/missing"]), "last_accessed": None}
    monkeypatch.setattr("crawler.requests.get", Mock(side_effect=error))

    assert crawler.download_web_page(host) is None
    assert isinstance(host["last_accessed"], datetime)
    crawler.logger.warning.assert_called()


def test_parse_web_page_handles_none_and_non_html(crawler):
    crawler.parse_web_page(None)
    crawler.parse_web_page(FakeResponse(url="https://example.com/file.pdf", content_type="application/pdf"))

    crawler.logger.warning.assert_called_with("No web page supplied for parsing.")
    crawler.logger.info.assert_any_call("Skipping non-HTML content: https://example.com/file.pdf")


def test_parse_web_page_adds_absolute_relative_and_fragment_links(monkeypatch, crawler):
    added = []

    def record(url):
        added.append(url)
        crawler.crawled_urls.add(url)

    monkeypatch.setattr(crawler, "add_url_to_frontier", record)
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

    assert added == [
        "https://example.com/absolute",
        "https://example.com/base/relative",
        "https://example.com/base/index.html#local",
    ]
    crawler.logger.info.assert_called_with("Parsed https://example.com/base/index.html; added 3 link(s) to frontier.")


def test_parse_web_page_catches_parser_errors(monkeypatch, crawler):
    monkeypatch.setattr("crawler.BeautifulSoup", Mock(side_effect=RuntimeError("bad html")))

    crawler.parse_web_page(FakeResponse(url="https://example.com/broken", text="<html>"))

    crawler.logger.warning.assert_called()


def test_crawl_downloads_parses_and_stops_when_frontier_empty(monkeypatch, crawler):
    response = FakeResponse(url="https://example.com/page", text="<html></html>")
    crawler.frontier["example.com"] = {"queue": deque(["https://example.com/page"]), "last_accessed": None}

    def download_once(host):
        host["queue"].popleft()
        return response

    download = Mock(side_effect=download_once)
    parse = Mock()
    monkeypatch.setattr(crawler, "download_web_page", download)
    monkeypatch.setattr(crawler, "parse_web_page", parse)

    crawler.crawl()

    assert crawler.pages_crawled == 1
    download.assert_called_once_with(crawler.frontier["example.com"])
    parse.assert_called_once_with(response)


def test_crawl_respects_crawl_limit(monkeypatch, crawler):
    crawler.crawl_limit = 1
    crawler.frontier["example.com"] = {"queue": deque(["https://example.com/1", "https://example.com/2"]), "last_accessed": None}
    monkeypatch.setattr(crawler, "download_web_page", Mock(return_value=FakeResponse()))
    monkeypatch.setattr(crawler, "parse_web_page", Mock())

    crawler.crawl()

    assert crawler.pages_crawled == 1
    assert len(crawler.frontier["example.com"]["queue"]) == 2


def test_crawl_does_not_count_failed_download(monkeypatch, crawler):
    crawler.frontier["example.com"] = {"queue": deque(["https://example.com/fail"]), "last_accessed": None}

    def fail_download(host):
        host["queue"].popleft()
        return None

    monkeypatch.setattr(crawler, "download_web_page", Mock(side_effect=fail_download))
    parse = Mock()
    monkeypatch.setattr(crawler, "parse_web_page", parse)

    crawler.crawl()

    assert crawler.pages_crawled == 0
    parse.assert_not_called()


def test_crawl_waits_when_all_hosts_are_inside_politeness_window(monkeypatch, crawler):
    host = {"queue": deque(["https://example.com/later"]), "last_accessed": datetime.now()}
    crawler.frontier["example.com"] = host
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)
        host["queue"].clear()

    monkeypatch.setattr("crawler.sleep", fake_sleep)

    crawler.crawl()

    assert slept and slept[0] >= 0.1
    assert crawler.pages_crawled == 0


def test_crawl_empty_frontier_finishes_without_download(monkeypatch, crawler):
    download = Mock()
    monkeypatch.setattr(crawler, "download_web_page", download)

    crawler.crawl()

    download.assert_not_called()
    crawler.logger.info.assert_any_call("Crawler frontier is empty. Crawl complete.")
