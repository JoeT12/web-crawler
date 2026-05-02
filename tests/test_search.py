from search import Search
import math
import sys
import types
from pathlib import Path

import pytest

""" Disclaimer: All test code in this file was generated entirely by ChatGPT (5.5 thinking model).
    
    ChatGPT was given the context of the implemented search.py file and
    the following prompt:
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


class ImportOnlyIndexer:
    """ Mock Indexer Import """

    def __init__(self, logger):
        self.logger = logger

    def load_index(self):
        pass


indexer_module.Indexer = ImportOnlyIndexer
sys.modules["indexer"] = indexer_module


class FakeLogger:
    """ Mock logger """

    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def warning(self, message):
        self.messages.append(("warning", message))

    def error(self, message):
        self.messages.append(("error", message))


class FakeIndexer:
    """ Mock Indexer class """

    def __init__(self, inverted_index=None, documents=None, urls=None, tokens=None):
        self.inverted_index = inverted_index or {}
        self.documents = documents if documents is not None else {
            1: {}, 2: {}, 3: {}, 4: {}}
        self.urls = urls or {}
        self.tokens = tokens
        self.requested_terms = []

    def tokenise_tag_content(self, content):
        """ Mock tokenise function.

        Args:
            content (list): A list of content to be tokenised.

        Returns:
            list: A list of tokens.
        """
        if self.tokens is not None:
            return self.tokens
        return [token.lower() for text in content for token in text.split()]

    def get_inverted_index(self, token):
        """ Mock getter for the inverted index.

        Args:
            token (str): A token to get the inverted index postings for.

        Returns:
            dict: All postings for the token in the inverted index.
        """
        self.requested_terms.append(token)
        return self.inverted_index.get(token, {})

    def get_url_for_document(self, document_id):
        """ Mock function to get URL for a given document id.

        Args:
            document_id (int): The document id to get the URL for.

        Returns:
            str: The URL that corresponds to the document id.
        """
        return self.urls.get(document_id)


@pytest.fixture
def logger():
    """ Mock log initialiser """
    return FakeLogger()


@pytest.fixture
def populated_indexer():
    """ Populates the mock inverted index with data.
    """

    return FakeIndexer(
        inverted_index={
            "alpha": {
                1: {"term_frequency": 1, "score": 0.0},
                2: {"term_frequency": 3, "score": 0.0},
                3: {"term_frequency": 1, "score": 0.0},
            },
            "beta": {
                1: {"term_frequency": 2, "score": 0.0},
                2: {"term_frequency": 1, "score": 0.0},
                4: {"term_frequency": 1, "score": 0.0},
            },
            "gamma": {3: {"term_frequency": 1, "score": 0.0}},
        },
        urls={
            1: "https://example.com/one",
            2: "https://example.com/two",
            3: "https://example.com/three",
            4: "https://example.com/four",
        },
    )


def test_constructor_loads_index_when_no_indexer_is_supplied(monkeypatch, logger):
    """ Ensures that the constructor automatically loads the Indexer if no index is explicitly
        supplied.

        Args:
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
            logger (logger): A mock logger object.
    """

    created = {}

    class LoadingIndexer:
        # Mock a loading indexer.
        documents = {}

        def __init__(self, received_logger):
            created["logger"] = received_logger
            created["loaded"] = False

        def load_index(self):
            created["loaded"] = True

    monkeypatch.setattr("search.Indexer", LoadingIndexer)
    searcher = Search(logger)

    # Assert that the Search class has loaded its own indexer.
    assert searcher.indexer.__class__ is LoadingIndexer
    assert created == {"logger": logger, "loaded": True}


def test_tokenise_query_returns_tokens_from_indexer(logger):
    """ Ensures that when asked to tokenise a query, the Search module successfully tokenises
        the query.

        Args:
            logger (logger): A mock logger object.
    """

    # Mock the Search component with our mock Indexer.
    searcher = Search(logger, indexer=FakeIndexer(tokens=["hello", "world"]))

    # Assert that tokens are as expected, and a message has been logged.
    assert searcher.tokenise_query("Hello WORLD") == ["hello", "world"]
    assert logger.messages[-1] == ("info", "Tokenised query into 2 tokens")


@pytest.mark.parametrize("query", [None, "", []])
def test_tokenise_query_rejects_missing_queries(query, logger):
    """ Ensures that when asked to tokenise a query that is missing, the Search class
        doesn't crash and handles the error gracefully.

        Args:
            query (str): A query parameter to pass to the tokenise_query function we are testing.
            logger (logger): A mock logger object.
    """

    # Mock the Search component with our mock Indexer.
    searcher = Search(logger, indexer=FakeIndexer())

    # Assert that the function returned without error and that a warning message was logged.
    assert searcher.tokenise_query(query) == []
    assert logger.messages[-1][0] == "warning"


def test_tokenise_query_handles_indexer_errors(logger):
    """ Ensures that when the indexer tokeniser errors, the Search component handles the error
        gracefully.

        Args:
            logger (logger): A mock logger object.
    """

    # Mock a broken Indexer that throws an error in the tokenisation process.
    class BrokenIndexer(FakeIndexer):
        def tokenise_tag_content(self, content):
            raise RuntimeError("tokeniser failed")

    # Mock the Search component with our broken mock Indexer.
    searcher = Search(logger, indexer=BrokenIndexer())

    # Assert that the search function didn't error and logged an error message.
    assert searcher.tokenise_query("query") == []
    assert logger.messages[-1][0] == "error"


def test_search_index_returns_documents_containing_all_unique_query_tokens(logger, populated_indexer):
    """ Ensures that the search_index function of the Search module returns documents containing all of the
        provided terms in the query. 

        Args:
            logger (logger): A mock logger object.
            populated_indexer: (Indexer): A mock indexer that is populated with an inverted index.
    """

    # Mock the Search component with our populated mock Indexer.
    searcher = Search(logger, indexer=populated_indexer)

    results = searcher.search_index(["alpha", "beta", "alpha"])

    # Assert that all the expected documents have been returned.
    assert list(results) == [1, 2]
    assert set(results[1]) == {"alpha", "beta"}
    assert results[2]["alpha"] == {"term_frequency": 3, "score": 0.0}
    assert populated_indexer.requested_terms == ["alpha", "beta"]


@pytest.mark.parametrize("tokens", [None, [], ()])
def test_search_index_rejects_missing_tokens(tokens, logger):
    """ Ensures that when the search_index function of the Search module is provided with an invalid 
        (list) of tokens, it rejects the tokens but does not error or crash. 

        Args:
            tokens: (list): A parameterised list of tokens.
            logger (logger): A mock logger object.
    """

    # Mock Search module with our fake indexer.
    searcher = Search(logger, indexer=FakeIndexer())

    # Assert that the search_index function returned and that a warning was logged.
    assert searcher.search_index(tokens) == {}
    assert logger.messages[-1][0] == "warning"


def test_search_index_returns_empty_when_a_query_term_has_no_postings(logger, populated_indexer):
    """ Ensures that the search_index function of the Search module returns an empty dictionary 
        when the query has no postings.

        Args:
            logger (logger): A mock logger object.
            populated_indexer: (Indexer): A mock indexer that is populated with an inverted index.
    """

    # Mock search module with our populated indexer.
    searcher = Search(logger, indexer=populated_indexer)

    # Assert that the function returned an empty dictionary and that only info messages were logged.
    assert searcher.search_index(["alpha", "missing"]) == {}
    assert logger.messages[-1][0] == "info"


def test_search_index_returns_empty_when_terms_do_not_intersect(logger, populated_indexer):
    """ Ensures that the search_index function of the Search module returns an empty dictionary 
        when the intersection of the query terms cannot be found in any documents.

        Args:
            logger (logger): A mock logger object.
            populated_indexer: (Indexer): A mock indexer that is populated with an inverted index.
    """

    # Mock search module with our populated mock indexer.
    searcher = Search(logger, indexer=populated_indexer)

    # Assert that the function returned an empty dictionary and that only info messages were logged.
    assert searcher.search_index(["beta", "gamma"]) == {}
    assert logger.messages[-1][0] == "info"


def test_search_index_handles_indexer_errors(logger):
    """ Ensures that the search_index function of the Search module handles any error with
        the Indexer gracefully.

        Args:
            logger (logger): A mock logger object.
    """

    # Mock a broken indexer for testing that throws a runtime error when trying to get the
    #  inverted index.
    class BrokenIndexer(FakeIndexer):
        def get_inverted_index(self, token):
            raise RuntimeError("index failed")

    # Mock search module with our broken mock indexer.
    searcher = Search(logger, indexer=BrokenIndexer())

    # Assert that the function returned an empty dictionary and that an error message was logged.
    assert searcher.search_index(["alpha"]) == {}
    assert logger.messages[-1][0] == "error"


def test_intersect_document_ids_finds_matches_and_uses_numeric_ordering(logger):
    """ Ensures that the intersect_document_ids function of the Search module correctly finds
        matches and uses NUMERIC ordering.

        Args:
            logger (logger): A mock logger object.
    """

    # Mock Search module with mock indexer injected.
    searcher = Search(logger, indexer=FakeIndexer())
    # Mock document id lists to intersect.
    left = [number for number in range(0, 30, 2)]
    right = [number for number in range(0, 30, 4)]

    # Assert that the intersections returned are as expected.
    assert searcher.intersect_document_ids(
        left, right) == [0, 4, 8, 12, 16, 20, 24, 28]


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [([], [1], []), ([1], [], []),
     (["a", "b"], ["b", "c"], ["b"]), ([1], [2], [])],
)
def test_intersect_document_ids_handles_boundaries(left, right, expected, logger):
    """ Ensures that the intersect_document_ids function of the Search module correctly
        handles boundary cases.

        Args:
            left (list): The first list of document ids to intersect.
            right (list): The second list of document ids to intersect.
            expected (list): The expected intersection list.
            logger (logger): A mock logger object.
    """

    # Mock a Search module with our fake Indexer.
    searcher = Search(logger, indexer=FakeIndexer())

    # Assert that the intersections returned are as expected.
    assert searcher.intersect_document_ids(left, right) == expected


def test_score_document_uses_tfidf_and_topical_score(logger):
    """ Ensures that when scoring the documents, the Search module uses both TFIDF and
        topical score.

        Args:
            logger (logger): A mock logger object.
    """

    # A mock Indexer initialised with a documents map and an inverted index.
    indexer = FakeIndexer(
        documents={1: {}, 2: {}, 3: {}},
        inverted_index={"alpha": {1: {}, 2: {}}, "beta": {1: {}}},
    )
    # A mock Search module injected with the mock indexer.
    searcher = Search(logger, indexer=indexer)
    # A mock posting to be scored.
    posting = {
        "alpha": {"term_frequency": 2, "score": 0.5},
        "beta": {"term_frequency": 1, "score": 0.25},
    }

    # Assert that the score is as expected.
    expected = round((2 * (math.log(4 / 2) + 1) + 0.5) +
                     (math.log(4 / 1) + 1 + 0.25), 6)
    assert searcher.score_document(
        ["alpha", "missing", "beta"], posting) == expected


@pytest.mark.parametrize("tokens, posting", [([], {"alpha": {}}), (["alpha"], {}), (None, None)])
def test_score_document_returns_zero_for_missing_inputs(tokens, posting, logger):
    """ Ensures that when scoring the documents, the Search module returns 0 as the score
        if any inputs are found to be missing.

        Args:
            tokens (list): A list of search query tokens.
            posting (dict): A dictionary of postings.
            logger (logger): A mock logger object.
    """

    # A mock Search module injected with the mock indexer.
    searcher = Search(logger, indexer=FakeIndexer())
    # Assert that the score with the parameterised values is 0.
    assert searcher.score_document(tokens, posting) == 0.0


def test_score_document_defaults_missing_posting_fields_to_zero(logger):
    """ Ensures that when scoring the documents, the Search module classifies any missing
        posting field as a zero.

        Args:
            logger (logger): A mock logger object.
    """

    # A mock Indexer initialised with a documents map and an inverted index.
    indexer = FakeIndexer(documents={}, inverted_index={"alpha": {1: {}}})
    # A mock Search module injected with the mock indexer.
    searcher = Search(logger, indexer=indexer)

    # Assert that the score returned is 0.
    assert searcher.score_document(["alpha"], {"alpha": {}}) == 0.0


def test_score_document_handles_indexer_errors(logger):
    """ Ensures that when scoring the documents, the Search module can gracefully handle any
        errors that occur within the indexer.

        Args:
            logger (logger): A mock logger object.
    """

    class BrokenIndexer(FakeIndexer):
        # A broken mock indexer that throws an error when getting the inverted index.
        documents = {1: {}}

        def get_inverted_index(self, token):
            raise RuntimeError("df failed")

    # A mock Search module injected with the mock indexer.
    searcher = Search(logger, indexer=BrokenIndexer())

    # Assert that the document that encountered an index error was scored as 0; and the error was logged.
    assert searcher.score_document(
        ["alpha"], {"alpha": {"term_frequency": 1}}) == 0.0
    assert logger.messages[-1][0] == "error"


def test_search_ranks_matching_urls_and_respects_result_limit(logger, populated_indexer):
    """ Ensures that the search_index function of the Search module ranks the URLs via their
        TFIDF scoring and only returns the limit requested.

        Args:
            logger (logger): A mock logger object.
            populated_indexer: (Indexer): A mock indexer that is populated with an inverted index.
    """

    # A mock Search module injected with the populated mock indexer.
    # Max number of documents returned set to 2.
    searcher = Search(logger, max_documents_returned=2,
                      indexer=populated_indexer)

    # Assert that the documents returned are as expected, and that a message was logged for successful retrieval.
    assert searcher.search_query("alpha beta") == [
        "https://example.com/two", "https://example.com/one"]
    assert logger.messages[-1] == ("info", "Search returned 2 URLs")


def test_search_returns_empty_when_query_has_no_tokens(logger):
    """ Ensures that the search_index function of the Search module returns an empty list
        when query has no tokens.

        Args:
            logger (logger): A mock logger object.
    """

    # A mock Search module injected with the mock indexer.
    searcher = Search(logger, indexer=FakeIndexer(tokens=[]))

    # Assert that the result was empty and that a warning message was logged.
    assert searcher.search_query("!!!") == []
    assert logger.messages[-1][0] == "warning"


def test_search_returns_empty_when_no_postings_match(logger, populated_indexer):
    """ Ensures that the search_index function of the Search module returns an empty list
        when no postings match the query.

        Args:
            logger (logger): A mock logger object.
            populated_indexer: (Indexer): A mock indexer that is populated with an inverted index.
    """

    # A mock Search module injected with the populated mock indexer.
    searcher = Search(logger, indexer=populated_indexer)

    # Assert that an empty list was returned and that an info message was logged to show no postings
    # were found.
    assert searcher.search_query("alpha missing") == []
    assert logger.messages[-1] == ("info", "No search results found")


def test_search_skips_zero_scores_and_missing_urls(logger):
    """ Ensures that the search_index function of the Search module skips postings with
        zero scores, and documents with missing URLs.

        Args:
            logger (logger): A mock logger object.
    """

    # Mock postings and Search module.
    postings = {1: {"id": 1}, 2: {"id": 2}, 3: {"id": 3}}
    searcher = Search(logger, max_documents_returned=3, indexer=FakeIndexer(
        urls={3: "https://example.com/three"}))

    # Mock return values for Search module functions.
    searcher.tokenise_query = lambda query: ["alpha"]
    searcher.search_index = lambda tokens: postings
    searcher.score_document = lambda tokens, posting: {
        1: 0.0, 2: 2.0, 3: 1.0}[posting["id"]]

    # Assert that only the expected URL was returned.
    assert searcher.search_query("alpha") == ["https://example.com/three"]


def test_search_handles_unexpected_errors(logger):
    """ Ensures that the search_index function of the Search module handles any unexpected
        errors gracefully.

        Args:
            logger (logger): A mock logger object.
    """

    # Mock Search module.
    searcher = Search(logger, indexer=FakeIndexer())
    # Mock an error being thrown in the tokenise_query function of the Search module.
    searcher.tokenise_query = lambda query: (
        _ for _ in ()).throw(RuntimeError("search failed"))

    # Check that search simply returned an empty list (didn't crash); and that an
    # error message was logged in the console.
    assert searcher.search_query("alpha") == []
    assert logger.messages[-1][0] == "error"
