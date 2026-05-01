import math
import sys
import types
from pathlib import Path

import pytest

""" Disclaimer: All test code in this file was generated entirely by ChatGPT (5.5 thinking model).
    
    ChatGPT was given the context of the implemented search.py file, and given 
    the following prompt
    - "Imagine you are an experienced software developer that has been tasked with implementing a web crawler for an
       upcoming search engine company. The code for searching an index has been provided and implemented by your team; 
       and now you have been tasked to write a high-coverage (>90%) test file for the implementation. You have been given 
       instructions by the team to ensure all edge and boundary cases are covered, and that the tests are written as concisely, 
       efficiently and as readable as possible."

    NOTE: To demonstrate our understanding of all the code written, we wrote all comments and documentation comments
    ourselves. The GenAI did not create any comments. We did, however, ask the GenAI to check and make changes
    for ONLY spelling/grammar/styling mistakes.
"""

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

indexer_module = types.ModuleType("indexer")
from search import Search

class ImportOnlyIndexer:
    def __init__(self, logger):
        self.logger = logger

    def load_index(self):
        pass


indexer_module.Indexer = ImportOnlyIndexer
sys.modules["indexer"] = indexer_module


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def warning(self, message):
        self.messages.append(("warning", message))

    def error(self, message):
        self.messages.append(("error", message))


class FakeIndexer:
    def __init__(self, inverted_index=None, documents=None, urls=None, tokens=None):
        self.inverted_index = inverted_index or {}
        self.documents = documents if documents is not None else {
            "1": {}, "2": {}, "3": {}, "4": {}}
        self.urls = urls or {}
        self.tokens = tokens
        self.requested_terms = []

    def tokenise_tag_content(self, content):
        if self.tokens is not None:
            return self.tokens
        return [token.lower() for text in content for token in text.split()]

    def get_inverted_index(self, token):
        self.requested_terms.append(token)
        return self.inverted_index.get(token, {})

    def get_url_for_document(self, document_id):
        return self.urls.get(document_id)


@pytest.fixture
def logger():
    return FakeLogger()


@pytest.fixture
def populated_indexer():
    return FakeIndexer(
        inverted_index={
            "alpha": {
                "1": {"term_frequency": 1, "score": 0.0},
                "2": {"term_frequency": 3, "score": 0.0},
                "3": {"term_frequency": 1, "score": 0.0},
            },
            "beta": {
                "1": {"term_frequency": 2, "score": 0.0},
                "2": {"term_frequency": 1, "score": 0.0},
                "4": {"term_frequency": 1, "score": 0.0},
            },
            "gamma": {"3": {"term_frequency": 1, "score": 0.0}},
        },
        urls={
            "1": "https://example.com/one",
            "2": "https://example.com/two",
            "3": "https://example.com/three",
            "4": "https://example.com/four",
        },
    )


def test_constructor_loads_index_when_no_indexer_is_supplied(monkeypatch, logger):
    created = {}

    class LoadingIndexer:
        documents = {}

        def __init__(self, received_logger):
            created["logger"] = received_logger
            created["loaded"] = False

        def load_index(self):
            created["loaded"] = True

    monkeypatch.setattr("search.Indexer", LoadingIndexer)
    searcher = Search(logger)

    assert searcher.indexer.__class__ is LoadingIndexer
    assert created == {"logger": logger, "loaded": True}


def test_tokenise_query_returns_tokens_from_indexer(logger):
    searcher = Search(logger, indexer=FakeIndexer(tokens=["hello", "world"]))

    assert searcher.tokenise_query("Hello WORLD") == ["hello", "world"]
    assert logger.messages[-1] == ("info", "Tokenised query into 2 tokens")


@pytest.mark.parametrize("query", [None, "", []])
def test_tokenise_query_rejects_missing_queries(query, logger):
    searcher = Search(logger, indexer=FakeIndexer())

    assert searcher.tokenise_query(query) == []
    assert logger.messages[-1][0] == "warning"


def test_tokenise_query_handles_indexer_errors(logger):
    class BrokenIndexer(FakeIndexer):
        def tokenise_tag_content(self, content):
            raise RuntimeError("tokeniser failed")

    searcher = Search(logger, indexer=BrokenIndexer())

    assert searcher.tokenise_query("query") == []
    assert logger.messages[-1][0] == "error"


def test_search_index_returns_documents_containing_all_unique_query_tokens(logger, populated_indexer):
    searcher = Search(logger, indexer=populated_indexer)

    results = searcher.search_index(["alpha", "beta", "alpha"])

    assert list(results) == ["1", "2"]
    assert set(results["1"]) == {"alpha", "beta"}
    assert results["2"]["alpha"] == {"term_frequency": 3, "score": 0.0}
    assert populated_indexer.requested_terms == ["alpha", "beta"]


@pytest.mark.parametrize("tokens", [None, [], ()])
def test_search_index_rejects_missing_tokens(tokens, logger):
    searcher = Search(logger, indexer=FakeIndexer())

    assert searcher.search_index(tokens) == {}
    assert logger.messages[-1][0] == "warning"


def test_search_index_returns_empty_when_a_query_term_has_no_postings(logger, populated_indexer):
    searcher = Search(logger, indexer=populated_indexer)

    assert searcher.search_index(["alpha", "missing"]) == {}
    assert logger.messages[-1][0] == "info"


def test_search_index_returns_empty_when_terms_do_not_intersect(logger, populated_indexer):
    searcher = Search(logger, indexer=populated_indexer)

    assert searcher.search_index(["beta", "gamma"]) == {}
    assert logger.messages[-1][0] == "info"


def test_search_index_handles_indexer_errors(logger):
    class BrokenIndexer(FakeIndexer):
        def get_inverted_index(self, token):
            raise RuntimeError("index failed")

    searcher = Search(logger, indexer=BrokenIndexer())

    assert searcher.search_index(["alpha"]) == {}
    assert logger.messages[-1][0] == "error"


def test_intersect_document_ids_finds_matches_and_uses_numeric_ordering(logger):
    searcher = Search(logger, indexer=FakeIndexer())
    left = [str(number) for number in range(0, 30, 2)]
    right = [str(number) for number in range(0, 30, 4)]

    assert searcher.intersect_document_ids(
        left, right) == ["0", "4", "8", "12", "16", "20", "24", "28"]


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [([], ["1"], []), (["1"], [], []),
     (["a", "b"], ["b", "c"], ["b"]), (["1"], ["2"], [])],
)
def test_intersect_document_ids_handles_boundaries(left, right, expected, logger):
    searcher = Search(logger, indexer=FakeIndexer())

    assert searcher.intersect_document_ids(left, right) == expected


def test_intersect_document_ids_handles_comparison_errors(logger):
    searcher = Search(logger, indexer=FakeIndexer())
    searcher.document_sort_key = lambda document_id: object()

    assert searcher.intersect_document_ids(["1"], ["2"]) == []
    assert logger.messages[-1][0] == "error"


@pytest.mark.parametrize(
    ("document_id", "expected"),
    [("10", 10), (7, 7), ("abc", "abc"), (None, "None")],
)
def test_document_sort_key_returns_numeric_keys_where_possible(document_id, expected, logger):
    searcher = Search(logger, indexer=FakeIndexer())

    assert searcher.document_sort_key(document_id) == expected


def test_score_document_uses_tfidf_and_topical_score(logger):
    indexer = FakeIndexer(
        documents={"1": {}, "2": {}, "3": {}},
        inverted_index={"alpha": {"1": {}, "2": {}}, "beta": {"1": {}}},
    )
    searcher = Search(logger, indexer=indexer)
    posting = {
        "alpha": {"term_frequency": 2, "score": 0.5},
        "beta": {"term_frequency": 1, "score": 0.25},
    }

    expected = round((2 * (math.log(4 / 2) + 1) + 0.5) +
                     (math.log(4 / 1) + 1 + 0.25), 6)

    assert searcher.score_document(
        ["alpha", "missing", "beta"], posting) == expected


@pytest.mark.parametrize("tokens, posting", [([], {"alpha": {}}), (["alpha"], {}), (None, None)])
def test_score_document_returns_zero_for_missing_inputs(tokens, posting, logger):
    searcher = Search(logger, indexer=FakeIndexer())

    assert searcher.score_document(tokens, posting) == 0.0


def test_score_document_defaults_missing_posting_fields_to_zero(logger):
    indexer = FakeIndexer(documents={}, inverted_index={"alpha": {"1": {}}})
    searcher = Search(logger, indexer=indexer)

    assert searcher.score_document(["alpha"], {"alpha": {}}) == 0.0


def test_score_document_handles_indexer_errors(logger):
    class BrokenIndexer(FakeIndexer):
        documents = {"1": {}}

        def get_inverted_index(self, token):
            raise RuntimeError("df failed")

    searcher = Search(logger, indexer=BrokenIndexer())

    assert searcher.score_document(
        ["alpha"], {"alpha": {"term_frequency": 1}}) == 0.0
    assert logger.messages[-1][0] == "error"


def test_search_ranks_matching_urls_and_respects_result_limit(logger, populated_indexer):
    searcher = Search(logger, max_documents_returned=2,
                      indexer=populated_indexer)

    assert searcher.search("alpha beta") == [
        "https://example.com/two", "https://example.com/one"]
    assert logger.messages[-1] == ("info", "Search returned 2 URLs")


def test_search_returns_empty_when_query_has_no_tokens(logger):
    searcher = Search(logger, indexer=FakeIndexer(tokens=[]))

    assert searcher.search("!!!") == []
    assert logger.messages[-1][0] == "warning"


def test_search_returns_empty_when_no_postings_match(logger, populated_indexer):
    searcher = Search(logger, indexer=populated_indexer)

    assert searcher.search("alpha missing") == []
    assert logger.messages[-1] == ("info", "No search results found")


def test_search_skips_zero_scores_and_missing_urls(logger):
    postings = {"1": {"id": "1"}, "2": {"id": "2"}, "3": {"id": "3"}}
    searcher = Search(logger, max_documents_returned=3, indexer=FakeIndexer(
        urls={"3": "https://example.com/three"}))
    searcher.tokenise_query = lambda query: ["alpha"]
    searcher.search_index = lambda tokens: postings
    searcher.score_document = lambda tokens, posting: {
        "1": 0.0, "2": 2.0, "3": 1.0}[posting["id"]]

    assert searcher.search("alpha") == ["https://example.com/three"]


def test_search_handles_unexpected_errors(logger):
    searcher = Search(logger, indexer=FakeIndexer())
    searcher.tokenise_query = lambda query: (
        _ for _ in ()).throw(RuntimeError("search failed"))

    assert searcher.search("alpha") == []
    assert logger.messages[-1][0] == "error"
