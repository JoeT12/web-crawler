import importlib
import json
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
    """A mock logger."""

    def __init__(self):
        self.messages = defaultdict(list)

    def info(self, message):
        self.messages["info"].append(message)

    def warning(self, message):
        self.messages["warning"].append(message)

    def error(self, message):
        self.messages["error"].append(message)


class StubStopWords:
    """A structure containing stopwords."""

    def words(self, _language):
        return ["a", "and", "is", "of", "the", "to"]


@pytest.fixture
def logger():
    """Instantiate a mock logger for injection into all tests."""
    return DummyLogger()


@pytest.fixture
def indexer(logger):
    """Instantiate a mock Indexer for injection into all tests."""
    return Indexer(logger)


@pytest.fixture
def soup():
    """Provide a BeautifulSoup-parsed dummy web page for injection into all tests."""
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
    """Ensure that the in-memory index and document map are empty when the Indexer is instantiated.

        Args:
            logger (logger): A mock logger for runtime logging.
    """

    subject = Indexer(logger)

    # Assert that both the in-memory index and the document map are empty.
    assert subject.index == {}
    assert subject.documents == {}
    assert subject.logger is logger


def test_map_content_to_tag_families_extracts_all_supported_fields(indexer, soup):
    """Ensure that, when asked to separate the document by tag families, the Indexer extracts all
        expected tag families and content.

        Args:
            indexer (Indexer): The mock Indexer.
            soup (BeautifulSoup): The parsed mock web page as a BeautifulSoup object.
    """

    # Pass the parsed mock web page to the indexer.
    result = indexer.map_content_to_tag_families(soup)

    # Assert that the extracted fields and their content are as expected.
    assert result["title"] == ["Test Page"]
    assert result["headings"] == ["Main Heading", "Secondary Heading"]
    assert result["links"] == ["First Link"]
    assert result["metadata"] == ["Search engine metadata"]
    assert any("Body text for the page." in body for body in result["body"])
    assert indexer.logger.messages["info"]


def test_map_content_to_tag_families_handles_missing_document(indexer):
    """Ensure that, when asked to separate the document by tag families, the Indexer does not crash
        if it is passed a None value.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    # Pass a None value to the function.
    result = indexer.map_content_to_tag_families(None)

    # Assert that the Indexer logged a message and returned an empty dictionary.
    assert result == {"title": [], "headings": [],
                      "body": [], "links": [], "metadata": []}
    assert "parsed document is missing" in indexer.logger.messages["warning"][0]


def test_map_content_to_tag_families_handles_documents_without_body(indexer):
    """Ensure that, when asked to separate the document by tag families, the Indexer does not crash
        if it is passed a document without an explicit body tag.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    # Mock HTML fragment with no body/header tags.
    parsed_fragment = BeautifulSoup(
        "<h1>Fragment Heading</h1><p>Fragment text</p>", "html.parser")

    # Call the function and assert that all text in the mock document was parsed as the body.
    result = indexer.map_content_to_tag_families(parsed_fragment)
    assert result["headings"] == ["Fragment Heading"]
    assert result["body"] == ["Fragment Heading Fragment text"]


def test_map_content_to_tag_families_logs_and_returns_defaults_on_parser_error(indexer):
    """Ensure that, when asked to separate the document by tag families, the Indexer does not crash
        if it is passed a document that results in a parser error.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    # A mock HTML document that fails during parsing.
    class BrokenDocument:
        title = None
        body = None

        def find_all(self, *_args, **_kwargs):
            raise RuntimeError("broken parser")

    # Call the function and assert that the error was logged and that an empty dictionary was returned.
    result = indexer.map_content_to_tag_families(BrokenDocument())
    assert result == {"title": [], "headings": [],
                      "body": [], "links": [], "metadata": []}
    assert "Failed to map tag families" in indexer.logger.messages["error"][0]


@pytest.fixture
def deterministic_nltk(monkeypatch):
    """Mock the behavior of the NLTK library for the following tests."""

    # Any call to get stopwords should return a custom list.
    monkeypatch.setattr(indexer_module.nltk.corpus,
                        "stopwords", StubStopWords())

    # Mock return values for the word_tokenize and pos_tag functions.
    monkeypatch.setattr(indexer_module.nltk, "word_tokenize",
                        lambda text: re.findall(r"[A-Za-z0-9'-]+", text))
    monkeypatch.setattr(indexer_module.nltk, "pos_tag", lambda words: [
                        (word, "NN") for word in words])


def test_tokenise_tag_content_returns_empty_list_for_empty_content(indexer):
    """Ensure that, when asked to tokenise empty tag content, the Indexer does not crash
        and returns an empty list.

        Args:
            indexer (Indexer): The mock Indexer.
    """
    assert indexer.tokenise_tag_content([]) == []
    assert indexer.tokenise_tag_content([None, "", "   "]) == []


def test_tokenise_tag_content_filters_splits_stems_and_adds_ngrams(indexer, deterministic_nltk):
    """Ensure that, when asked to tokenise tag content, the Indexer splits and stems words
        and extracts n-grams as tokens.

        Args:
            indexer (Indexer): The mock Indexer.
            deterministic_nltk (any): Applies monkeypatching before the test run for deterministic NLTK behavior.
    """

    # Call the function to tokenise with a mock list.
    tokens = indexer.tokenise_tag_content(
        ["Running state-of-the-art AI's a x robots 123!"])

    # Assert that the words were stemmed and that n-grams were recognised.
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
    # Ensure that all runtime messages logged were of info severity.
    assert indexer.logger.messages["info"]


def test_tokenise_tag_content_logs_and_returns_empty_list_on_nltk_error(indexer, monkeypatch):
    """Ensure that, when asked to tokenise tag content, the Indexer returns an empty list if NLTK
        raises an error.

        Args:
            indexer (Indexer): The mock Indexer.
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
    """

    # Mock the NLTK stopwords function being "broken."
    class BrokenStopWords:
        def words(self, _language):
            raise LookupError("missing corpus")

    monkeypatch.setattr(indexer_module.nltk.corpus,
                        "stopwords", BrokenStopWords())

    # Assert that no tokens were returned and that an error message was logged.
    assert indexer.tokenise_tag_content(["content"]) == []
    assert "Failed to tokenise tag content" in indexer.logger.messages["error"][0]


def test_build_postings_counts_positions_fields_and_weighted_scores(indexer):
    """Ensure that, when asked to build postings, the Indexer correctly calculates the posting fields
        and scores according to the implemented solution.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    # Ask the Indexer to build postings from some document features.
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

    # Assert that the posting fields and scoring are correct.
    assert result["alpha"]["term_frequency"] == 3
    assert result["alpha"]["positions"] == [0, 2, 5]
    assert result["alpha"]["fields"] == ["links", "title"]
    assert result["alpha"]["score"] == round(
        5.0 + 5.0 / 1.002 + 2.0 / 1.005, 6)
    assert result["beta"]["term_frequency"] == 2
    assert result["beta"]["fields"] == ["headings", "title"]
    assert result["epsilon"]["score"] == round(1.0 / 1.007, 6)


def test_build_postings_handles_empty_or_missing_tokens(indexer):
    """Ensure that, when asked to build postings, the Indexer does not crash if passed a None value
        or no tokens.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    # Assert that the Indexer returns an empty posting map.
    assert indexer.build_postings({}) == {}
    assert indexer.build_postings(None) == {}
    assert indexer.build_postings({"title": None, "body": []}) == {}


def test_build_postings_logs_and_returns_empty_dict_on_error(indexer):
    """Ensure that, when asked to build postings, the Indexer does not crash if tokenisation errors occur.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    # Mock a tokenisation error.
    class BrokenTokens:
        def items(self):
            raise RuntimeError("cannot iterate")

    # Assert that no postings were created and that an error was logged at runtime.
    assert indexer.build_postings(BrokenTokens()) == {}
    assert "Failed to build postings" in indexer.logger.messages["error"][0]


def test_index_page_indexes_new_urls_and_reuses_existing_document_ids(indexer, monkeypatch):
    """Ensure that the Indexer can index both new documents and updated existing documents.

        Args:
            indexer (Indexer): The mock Indexer.
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
    """

    # Mock the helper function return values.
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

    # Call the indexing function.
    indexer.index_page("https://example.com/one", object())
    indexer.index_page("https://example.com/one", object())
    indexer.index_page("https://example.com/two", object())

    # Assert that the Indexer created only two documents and that the information stored under the repeated document
    # in the inverted index is still correct.
    assert indexer.documents == {
        1: "https://example.com/one", 2: "https://example.com/two"}
    assert sorted(indexer.index["alpha"].keys()) == [1, 2]
    assert indexer.index["alpha"][1]["score"] == 5.0


def test_index_page_ignores_missing_inputs(indexer):
    """Ensure that the Indexer does not crash if no inputs are passed to it.

        Args:
            indexer (Indexer): The mock Indexer.
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
    """

    indexer.index_page("", object())
    indexer.index_page("https://example.com", None)

    # Assert that only warning messages were logged and that the inverted index and document map are empty.
    assert indexer.documents == {}
    assert indexer.index == {}
    assert len(indexer.logger.messages["warning"]) == 2


def test_index_page_logs_errors_without_raising(indexer, monkeypatch):
    """Ensure that if the Indexer encounters an error while indexing a page, it logs the error but does not raise it.

        Args:
            indexer (Indexer): The mock Indexer.
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
    """

    # Mock an error.
    def raise_error(_document):
        raise RuntimeError("mapping failed")

    # Mock a helper function used by the Indexer to raise the mocked error.
    monkeypatch.setattr(indexer, "map_content_to_tag_families", raise_error)

    # Call the Indexer function and assert that no errors are raised and that the error is logged.
    indexer.index_page("https://example.com", object())
    assert indexer.documents == {1: "https://example.com"}
    assert indexer.index == {}
    assert "Failed to index URL" in indexer.logger.messages["error"][0]


def test_save_index_writes_json_files_and_load_index_reads_them(tmp_path, logger, monkeypatch):
    """Ensure that the Indexer saves and loads JSON files correctly.

        Args:
            tmp_path (str): A mock path.
            logger (logger): A mock logger for runtime logging.
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
    """

    # Set up a fake module directory for test data.
    fake_module_file = tmp_path / "src" / "indexer.py"
    fake_module_file.parent.mkdir()
    monkeypatch.setattr(indexer_module, "__file__", str(fake_module_file))
    subject = Indexer(logger)
    subject.documents = {1: "https://example.com"}
    subject.index = {"alpha": {1: {"term_frequency": 1,
                                   "positions": [0], "fields": ["title"], "score": 5.0}}}
    subject.save_index()

    # Assert that the data loaded from the JSON files into the Indexer is as expected.
    data_dir = tmp_path / "data"
    assert json.loads((data_dir / "documents.json").read_text(encoding="utf-8")
                      ) == {"1": "https://example.com"}
    assert json.loads(
        (data_dir / "index.json").read_text(encoding="utf-8")
    ) == {
        "alpha": {
            "1": {
                "term_frequency": 1,
                "positions": [0],
                "fields": ["title"],
                "score": 5.0,
            }
        }
    }
    reloaded = Indexer(logger)
    reloaded.load_index()
    assert reloaded.documents == {1: "https://example.com"}
    assert reloaded.index == subject.index


def test_load_index_uses_empty_dicts_when_files_do_not_exist(tmp_path, logger, monkeypatch):
    """Ensure that the Indexer uses empty dictionaries and does not crash when the files do not
        exist.

        Args:
            tmp_path (str): A mock path.
            logger (logger): A mock logger for runtime logging.
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
    """

    # Set up a fake module directory for test data.
    fake_module_file = tmp_path / "src" / "indexer.py"
    fake_module_file.parent.mkdir()
    monkeypatch.setattr(indexer_module, "__file__", str(fake_module_file))

    # Instantiate the Indexer and write some temporary data into its state.
    subject = Indexer(logger)
    subject.documents = {1: "stale"}
    subject.index = {"stale": {}}

    # Assert that the Indexer state was reset after loading from an empty or non-existent file.
    subject.load_index()
    assert subject.documents == {}
    assert subject.index == {}


def test_load_index_resets_state_when_json_is_invalid(tmp_path, logger, monkeypatch, capsys):
    """Ensure that the Indexer uses empty dictionaries and does not crash when the JSON within the
        data files is malformed.

        Args:
            tmp_path (str): A mock path.
            logger (logger): A mock logger for runtime logging.
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
    """

    # Set up a fake module directory.
    fake_module_file = tmp_path / "src" / "indexer.py"
    fake_module_file.parent.mkdir()
    monkeypatch.setattr(indexer_module, "__file__", str(fake_module_file))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # Write some malformed JSON into the test files.
    (data_dir /
     "documents.json").write_text("{not valid json", encoding="utf-8")
    (data_dir / "index.json").write_text('{"alpha": {}}', encoding="utf-8")

    # Instantiate the Indexer and write some temporary data into its state.
    subject = Indexer(logger)
    subject.documents = {1: "stale"}
    subject.index = {"stale": {}}

    # Assert that the malformed JSON was not loaded into the Indexer and that an error was printed.
    subject.load_index()
    captured = capsys.readouterr()
    assert subject.documents == {}
    assert subject.index == {}
    assert "Failed to load index" in captured.out


def test_save_index_logs_errors_without_raising(logger, monkeypatch, capsys):
    """Ensure that, when asked to save index data, the Indexer logs errors but does not raise them.

        Args:
            logger (logger): A mock logger for runtime logging.
            monkeypatch (pytest.monkeyPatch.MonkeyPatch): A MonkeyPatch object used to modify
                functions at runtime for mocking.
    """

    # Mock an OS error during data saving.
    subject = Indexer(logger)
    monkeypatch.setattr(indexer_module.os, "makedirs", lambda *_args,
                        **_kwargs: (_ for _ in ()).throw(OSError("no permission")))

    # Assert that errors were printed and that none were raised.
    subject.save_index()
    captured = capsys.readouterr()
    assert "Failed to save index" in captured.out


def test_get_inverted_index_returns_postings_for_existing_term(indexer):
    """Ensure that the Indexer returns the postings for an existing term.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    indexer.index = {
        "alpha": {
            1: {"term_frequency": 2, "positions": [0, 3], "fields": ["title"], "score": 9.0}
        }
    }

    result = indexer.get_inverted_index("alpha")

    assert result == indexer.index["alpha"]
    assert "Retrieved 1 postings for term alpha" in indexer.logger.messages["info"][0]


def test_get_inverted_index_returns_empty_dict_for_missing_or_empty_term(indexer):
    """ Ensures that the Indexer handles missing and empty terms gracefully.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    indexer.index = {"alpha": {1: {"term_frequency": 1}}}

    assert indexer.get_inverted_index("beta") == {}
    assert indexer.get_inverted_index("") == {}
    assert "Retrieved 0 postings for term beta" in indexer.logger.messages["info"][0]
    assert "term is missing" in indexer.logger.messages["warning"][0]


def test_get_inverted_index_logs_and_returns_empty_dict_on_error(indexer):
    """ Ensures that the Indexer logs and returns an empty dictionary if index lookup fails.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    #  Mock a broken Indexer.
    class BrokenIndex:
        def get(self, *_args, **_kwargs):
            raise RuntimeError("cannot read index")

    indexer.index = BrokenIndex()

    #  Assert that when index cannot be ready, empty index is returned on index get request.
    # and an error is logged.
    assert indexer.get_inverted_index("alpha") == {}
    assert "Failed to get inverted index for term alpha" in indexer.logger.messages[
        "error"][0]


def test_get_url_for_document_returns_url_for_document_ids(indexer):
    """ Ensures that the Indexer returns URLs for document ids.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    indexer.documents = {1: "https://example.com/one",
                         2: "https://example.com/two"}

    assert indexer.get_url_for_document(1) == "https://example.com/one"
    assert indexer.get_url_for_document(1) == "https://example.com/one"
    assert indexer.get_url_for_document(2) == "https://example.com/two"


def test_get_url_for_document_returns_none_for_missing_document_id(indexer):
    """ Ensures that the Indexer returns None when a document id cannot be found.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    indexer.documents = {1: "https://example.com/one"}
    assert indexer.get_url_for_document(999) is None


def test_get_url_for_document_handles_none_document_id(indexer):
    """ Ensures that the Indexer handles a None document id gracefully.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    assert indexer.get_url_for_document(None) is None
    assert "document id is missing" in indexer.logger.messages["warning"][0]


def test_get_url_for_document_logs_and_returns_none_on_error(indexer):
    """ Ensures that the Indexer logs and returns None if document lookup fails.

        Args:
            indexer (Indexer): The mock Indexer.
    """

    # Mock a broken document map that cannot be read by the indexer.
    class BrokenDocuments:
        def get(self, *_args, **_kwargs):
            raise RuntimeError("cannot read documents")

    indexer.documents = BrokenDocuments()

    assert indexer.get_url_for_document(1) is None
    # Assert Indexer logs error message.
    assert "Failed to get URL for document 1" in indexer.logger.messages["error"][0]
