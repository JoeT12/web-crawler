import importlib
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

""" Disclaimer: All test code in this file was generated entirely by ChatGPT (5.5 thinking model).
    
    ChatGPT was given the context of the implemented indexer.py file, and given 
    the following prompt
    - "Imagine you are an experienced software developer that has been tasked with implementing a web crawler 
       for an upcoming search engine company. The code for indexing has been provided and implemented by your team; 
       and now you have been tasked to write a high-coverage (>90%) test file for the implementation. You have been 
       given instructions by the team to ensure all edge and boundary cases are covered, and that the tests are 
       written as concisely, efficiently and as readable as possible."

    NOTE: To demonstrate our understanding of all the code written, we wrote all comments and documentation comments
    ourselves. The GenAI did not create any comments. We did, however, ask the GenAI to check and make changes
    for ONLY spelling/grammar/styling mistakes.
"""

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

indexer_module = importlib.import_module("indexer")
Indexer = indexer_module.Indexer


class DummyLogger:
    def __init__(self):
        self.messages = defaultdict(list)

    def info(self, message):
        self.messages["info"].append(message)

    def warning(self, message):
        self.messages["warning"].append(message)

    def error(self, message):
        self.messages["error"].append(message)


@pytest.fixture
def logger():
    return DummyLogger()


@pytest.fixture
def indexer(logger):
    return Indexer(logger)


@pytest.fixture
def soup():
    return BeautifulSoup(
        """
        <html>
          <head>
            <title> Test Page </title>
            <meta name="description" content=" Search engine metadata ">
            <meta name="empty" content="">
          </head>
          <body>
            <h1>Main Heading</h1>
            <h2>Secondary Heading</h2>
            <a href="/one">First Link</a>
            <a href="/two"></a>
            <p>Body text for the page.</p>
          </body>
        </html>
        """,
        "html.parser",
    )


def test_init_starts_with_empty_index_and_document_map(logger):
    subject = Indexer(logger)

    # Assert that
    assert subject.index == {}
    assert subject.documents == {}
    assert subject.logger is logger


def test_map_content_to_tag_families_extracts_all_supported_fields(indexer, soup):
    result = indexer.map_content_to_tag_families(soup)

    assert result["title"] == ["Test Page"]
    assert result["headings"] == ["Main Heading", "Secondary Heading"]
    assert result["links"] == ["First Link"]
    assert result["metadata"] == ["Search engine metadata"]
    assert any("Body text for the page." in body for body in result["body"])
    assert indexer.logger.messages["info"]


def test_map_content_to_tag_families_handles_missing_document(indexer):
    result = indexer.map_content_to_tag_families(None)

    assert result == {"title": [], "headings": [],
                      "body": [], "links": [], "metadata": []}
    assert "parsed document is missing" in indexer.logger.messages["warning"][0]


def test_map_content_to_tag_families_handles_documents_without_body(indexer):
    parsed_fragment = BeautifulSoup(
        "<h1>Fragment Heading</h1><p>Fragment text</p>", "html.parser")

    result = indexer.map_content_to_tag_families(parsed_fragment)

    assert result["headings"] == ["Fragment Heading"]
    assert result["body"] == ["Fragment Heading Fragment text"]


def test_map_content_to_tag_families_logs_and_returns_defaults_on_parser_error(indexer):
    class BrokenDocument:
        title = None
        body = None

        def find_all(self, *_args, **_kwargs):
            raise RuntimeError("broken parser")

    result = indexer.map_content_to_tag_families(BrokenDocument())

    assert result == {"title": [], "headings": [],
                      "body": [], "links": [], "metadata": []}
    assert "Failed to map tag families" in indexer.logger.messages["error"][0]


class StubStopWords:
    def words(self, _language):
        return ["a", "and", "is", "of", "the", "to"]


@pytest.fixture
def deterministic_nltk(monkeypatch):
    monkeypatch.setattr(indexer_module.nltk.corpus,
                        "stopwords", StubStopWords())
    monkeypatch.setattr(indexer_module.nltk, "word_tokenize",
                        lambda text: re.findall(r"[A-Za-z0-9'-]+", text))
    monkeypatch.setattr(indexer_module.nltk, "pos_tag", lambda words: [
                        (word, "NN") for word in words])


def test_tokenise_tag_content_returns_empty_list_for_empty_content(indexer):
    assert indexer.tokenise_tag_content([]) == []
    assert indexer.tokenise_tag_content([None, "", "   "]) == []


def test_tokenise_tag_content_filters_splits_stems_and_adds_ngrams(indexer, deterministic_nltk):
    tokens = indexer.tokenise_tag_content(
        ["Running state-of-the-art AI's a x robots 123!"])

    assert "run" in tokens
    assert "state" in tokens
    assert "art" in tokens
    assert "ai" in tokens
    assert "robot" in tokens
    assert "123" in tokens
    assert "a" not in tokens
    assert "x" not in tokens
    assert "run_state" in tokens
    assert "run_state_art" in tokens
    assert any(token.startswith("run_state_art") for token in tokens)
    assert indexer.logger.messages["info"]


def test_tokenise_tag_content_logs_and_returns_empty_list_on_nltk_error(indexer, monkeypatch):
    class BrokenStopWords:
        def words(self, _language):
            raise LookupError("missing corpus")

    monkeypatch.setattr(indexer_module.nltk.corpus,
                        "stopwords", BrokenStopWords())

    assert indexer.tokenise_tag_content(["content"]) == []
    assert "Failed to tokenise tag content" in indexer.logger.messages["error"][0]


def test_build_postings_counts_positions_fields_and_weighted_scores(indexer):
    result = indexer.build_postings(
        {
            "title": ["alpha", "beta", "alpha"],
            "headings": ["beta"],
            "metadata": ["gamma"],
            "links": ["alpha"],
            "body": ["delta"],
            "unknown": ["epsilon"],
        }
    )

    assert result["alpha"]["term_frequency"] == 3
    assert result["alpha"]["positions"] == [0, 2, 5]
    assert result["alpha"]["fields"] == ["links", "title"]
    assert result["alpha"]["score"] == round(
        5.0 + 5.0 / 1.002 + 2.0 / 1.005, 6)
    assert result["beta"]["term_frequency"] == 2
    assert result["beta"]["fields"] == ["headings", "title"]
    assert result["epsilon"]["score"] == round(1.0 / 1.007, 6)


def test_build_postings_handles_empty_or_missing_tokens(indexer):
    assert indexer.build_postings({}) == {}
    assert indexer.build_postings(None) == {}
    assert indexer.build_postings({"title": None, "body": []}) == {}


def test_build_postings_logs_and_returns_empty_dict_on_error(indexer):
    class BrokenTokens:
        def items(self):
            raise RuntimeError("cannot iterate")

    assert indexer.build_postings(BrokenTokens()) == {}
    assert "Failed to build postings" in indexer.logger.messages["error"][0]


def test_index_page_indexes_new_urls_and_reuses_existing_document_ids(indexer, monkeypatch):
    monkeypatch.setattr(indexer, "map_content_to_tag_families",
                        lambda _document: {"title": ["content"]})
    monkeypatch.setattr(indexer, "tokenise_tag_content",
                        lambda _content: ["alpha"])
    monkeypatch.setattr(
        indexer,
        "build_postings",
        lambda _tokens: {"alpha": {"term_frequency": 1,
                                   "positions": [0], "fields": ["title"], "score": 5.0}},
    )

    indexer.index_page("https://example.com/one", object())
    indexer.index_page("https://example.com/one", object())
    indexer.index_page("https://example.com/two", object())

    assert indexer.documents == {
        1: "https://example.com/one", 2: "https://example.com/two"}
    assert sorted(indexer.index["alpha"].keys()) == ["1", "2"]
    assert indexer.index["alpha"]["1"]["score"] == 5.0


def test_index_page_ignores_missing_inputs(indexer):
    indexer.index_page("", object())
    indexer.index_page("https://example.com", None)

    assert indexer.documents == {}
    assert indexer.index == {}
    assert len(indexer.logger.messages["warning"]) == 2


def test_index_page_logs_errors_without_raising(indexer, monkeypatch):
    def raise_error(_document):
        raise RuntimeError("mapping failed")

    monkeypatch.setattr(indexer, "map_content_to_tag_families", raise_error)

    indexer.index_page("https://example.com", object())

    assert indexer.documents == {1: "https://example.com"}
    assert indexer.index == {}
    assert "Failed to index URL" in indexer.logger.messages["error"][0]


def test_save_index_writes_json_files_and_load_index_reads_them(tmp_path, logger, monkeypatch):
    fake_module_file = tmp_path / "src" / "indexer.py"
    fake_module_file.parent.mkdir()
    monkeypatch.setattr(indexer_module, "__file__", str(fake_module_file))

    subject = Indexer(logger)
    subject.documents = {1: "https://example.com"}
    subject.index = {"alpha": {"1": {"term_frequency": 1,
                                     "positions": [0], "fields": ["title"], "score": 5.0}}}

    subject.save_index()

    data_dir = tmp_path / "data"
    assert json.loads((data_dir / "documents.json").read_text(encoding="utf-8")
                      ) == {"1": "https://example.com"}
    assert json.loads(
        (data_dir / "index.json").read_text(encoding="utf-8")) == subject.index

    reloaded = Indexer(logger)
    reloaded.load_index()

    assert reloaded.documents == {"1": "https://example.com"}
    assert reloaded.index == subject.index


def test_load_index_uses_empty_dicts_when_files_do_not_exist(tmp_path, logger, monkeypatch):
    fake_module_file = tmp_path / "src" / "indexer.py"
    fake_module_file.parent.mkdir()
    monkeypatch.setattr(indexer_module, "__file__", str(fake_module_file))

    subject = Indexer(logger)
    subject.documents = {1: "stale"}
    subject.index = {"stale": {}}

    subject.load_index()

    assert subject.documents == {}
    assert subject.index == {}


def test_load_index_resets_state_when_json_is_invalid(tmp_path, logger, monkeypatch):
    fake_module_file = tmp_path / "src" / "indexer.py"
    fake_module_file.parent.mkdir()
    monkeypatch.setattr(indexer_module, "__file__", str(fake_module_file))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir /
     "documents.json").write_text("{not valid json", encoding="utf-8")
    (data_dir / "index.json").write_text('{"alpha": {}}', encoding="utf-8")

    subject = Indexer(logger)
    subject.documents = {1: "stale"}
    subject.index = {"stale": {}}

    subject.load_index()

    assert subject.documents == {}
    assert subject.index == {}
    assert "Failed to load index" in logger.messages["error"][0]


def test_save_index_logs_errors_without_raising(logger, monkeypatch):
    subject = Indexer(logger)
    monkeypatch.setattr(indexer_module.os, "makedirs", lambda *_args,
                        **_kwargs: (_ for _ in ()).throw(OSError("no permission")))

    subject.save_index()

    assert "Failed to save index" in logger.messages["error"][0]
