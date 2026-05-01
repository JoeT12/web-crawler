import json
import os
import re
from collections import defaultdict

import nltk
from nltk.stem import PorterStemmer

# To implement the indexer functionality, we used the lecture slides to write function stubs and
# detailed descriptions for implementation by a GenAI tool. The GenAI tool used to generate the
# implementations was ChatGPT (5.2 Thinking model). We note that we have not changed the function
# documentation comments throughout the development process to ensure full visibility as to the
# information provided to the GenAI for implementation; and that the AI was instructed to not
# add any comments to the implementations, to enable us to perform this process and check over the AI generated code.


# General guidance provided to the AI for all function implementation was as follows:
# 1. All code should be testable.
# 2. All code should handle errors gracefully to prevent crashes.
# 3. All code should be efficient, and concise as possible.
# 4. All code should use the logger to print helpful log messsages that can be used in any debugging.
# 5. Any added code should not be commented. (To allow for us to add comments ourselves).


class Indexer:
    def __init__(self, logger):
        # Inverted index.
        self.index = {}

        # Logger
        self.logger = logger

        # A map of integers to URL's for the inverted index.
        self.documents = {}

    def index_page(self, url, parsed_document):
        """ This function makes use of the helper functions: map_content_to_tag_families, tokenise_tag_content and build_postings to
            append postings to the in-memory inverted index. The document is identified in the inverted index by a document id, which
            is assigned to each distinct URL; such maps are stored seperately.

            Args:
                url (str): The url of the document that we are indexing.
                parsed_document (BeautifulSoup): The parsed web page.
        """
        try:
            if not url or parsed_document is None:
                self.logger.warning(
                    "Cannot index page because url or parsed document is missing")
                return

            # Assign the document an id, add the assigned document id and url to the map of documents.
            existing_document_ids = [int(
                document_id) for document_id, document_url in self.documents.items() if document_url == url]
            document_id = existing_document_ids[0] if existing_document_ids else (
                max([int(key) for key in self.documents.keys()], default=0) + 1)
            self.documents[document_id] = url

            # Get the postings of the document to add to the inverted index.
            tag_content = self.map_content_to_tag_families(parsed_document)
            document_tokens = {family: self.tokenise_tag_content(
                content) for family, content in tag_content.items()}
            postings = self.build_postings(document_tokens)

            #  Add the postings to the (in memory) inverted index.
            for term, posting in postings.items():
                self.index.setdefault(term, {})[str(document_id)] = posting

            self.logger.info(f"Indexed URL {url} as document {document_id}")
        except Exception as error:
            self.logger.error(f"Failed to index URL {url}: {error}")

    def get_inverted_index(self, term):
        """ This function returns the inverted index for a singular term.

            Args:
                word (str): A word to retrieve the inverted index postings for.

            Returns:
                dict: A list of inverted index postings for the term.
        """

    def get_url_for_document(self, document_id):
        """ This function will return the URL of the document with a given id using the Indexer documents map.

            Args:
                document_id (int): The numeric id of the document.

            Returns:
                dict: The URL that corresponds to that document.
        """

    def map_content_to_tag_families(self, parsed_document):
        """ This function takes a document parsed with BeautifulSoup, and creates a map of the content corresponding to a particular tag
            family in the document. For example, if the document has multiple headings, all such heading should be stored as a list under
            the headings key of the map.

            Args:
                parsed_document (BeautifulSoup): The parsed web page.

            Returns:
                dict: A map of HTML tag families to document contents.
        """
        tag_families = {"title": [], "headings": [],
                        "body": [], "links": [], "metadata": []}
        try:
            if parsed_document is None:
                self.logger.warning(
                    "Cannot map tag families because parsed document is missing")
                return tag_families

            if getattr(parsed_document, "title", None) and parsed_document.title.string:
                tag_families["title"].append(
                    parsed_document.title.string.strip())

            for tag in parsed_document.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                text = tag.get_text(" ", strip=True)
                if text:
                    tag_families["headings"].append(text)

            for tag in parsed_document.find_all("a"):
                text = tag.get_text(" ", strip=True)
                if text:
                    tag_families["links"].append(text)

            for tag in parsed_document.find_all("meta"):
                content = tag.get("content")
                if content:
                    tag_families["metadata"].append(content.strip())

            body = parsed_document.body if getattr(
                parsed_document, "body", None) else parsed_document
            text = body.get_text(" ", strip=True) if hasattr(
                body, "get_text") else ""
            if text:
                tag_families["body"].append(text)

            self.logger.info("Mapped parsed document content to tag families")
        except Exception as error:
            self.logger.error(f"Failed to map tag families: {error}")
        return tag_families

    def tokenise_tag_content(self, tag_content):
        """ This function takes a list of content that was enclosed within a family of HTML tags for a particular document, and tokenises it into individual terms.
            It handles: small words, hyphens, apostrophes and stop words carefully, disposing of them if they offer no additional meaning to the surrounding terms. It
            also stems words to using the porter stemmer to improve searching efficiency within the index and reducing the number of forms needed to be stored in the index.
            In addition, it should also detect phrases and n-grams using the part-of-speech tagging. It uses the NLTK Python to perform such functions wherever possible 
            to prevent "re-inventing the wheel".

            Reference:
            - Reference NLTK for Tokenisation: Bird, Steven, Edward Loper and Ewan Klein (2009), Natural Language Processing with Python. O'Reilly Media Inc.

            Args:
                tag_content (list): A map of HTML tag families to document contents.

            Returns:
                list: A tokenised version of the list provided.
        """
        try:
            if not tag_content:
                return []

            text = " ".join(str(content) for content in tag_content if content)
            if not text:
                return []

            # Use NLTK to get the English stopwords, and tokenise the tag content.
            stop_words = set(nltk.corpus.stopwords.words("english"))
            raw_tokens = nltk.word_tokenize(text)

            # Use NLTK stem the terms.
            stemmer = PorterStemmer()
            words = []
            for token in raw_tokens:
                # Converts token to lowercase, splits on hyphens/apostrophes.
                for part in re.split(r"[-']+", token.lower()):
                    # Remove any character from the token that is not a lowercase character or digit.
                    part = re.sub(r"[^a-z0-9]", "", part)
                    # If the token is not of length 1 and not in stop words, then stem it.
                    if len(part) > 1 and part not in stop_words:
                        words.append(stemmer.stem(part))

            # Use NLTK to extract the phrases.
            phrases = []
            if words:
                # Assigns each word to part of speech tag.
                tagged = nltk.pos_tag(words)
                # Defines a grammar rule called NP (noun phrase) for: 0+ adjectives. 1+ noun.
                grammar = r"NP: {<JJ.*>*<NN.*>+}"
                # Use the grammar to parse tagged words into a tree.
                tree = nltk.RegexpParser(grammar).parse(tagged)
                # keeps phrases with more than one word, joins words of a phrase with _.
                phrases = ["_".join(word for word, tag in subtree.leaves()) for subtree in tree.subtrees(
                    lambda subtree: subtree.label() == "NP") if len(subtree.leaves()) > 1]

            # Constructs a final list of tokens.
            bigrams = ["_".join(ngram) for ngram in zip(words, words[1:])]
            trigrams = ["_".join(ngram)
                        for ngram in zip(words, words[1:], words[2:])]
            tokens = words + phrases + bigrams + trigrams
            self.logger.info(
                f"Tokenised tag content into {len(tokens)} tokens")
            return tokens
        except Exception as error:
            self.logger.error(f"Failed to tokenise tag content: {error}")
            return []

    def build_postings(self, document_tokens):
        """ This function should build the postings for the inverted index. Each posting includes:
            1. Term frequency;
            2. Term position in the document;
            3. Term fields (i.e., what family of HTML tags it can be found under in the document).
            4. Term score that combines all the previous information to calculate how relevant the term is to the document.

            Args:
                document_tokens (dict): A map of HTML tag families to tokenised document content.

            Returns:
                dict: A map of postings.
        """

        # Prepare an empty postings object.
        postings = defaultdict(
            lambda: {"term_frequency": 0, "positions": [], "fields": set(), "score": 0.0})
        # Define weights to calculate the final score of each posting.
        field_weights = {"title": 5.0, "headings": 4.0,
                         "metadata": 3.0, "links": 2.0, "body": 1.0}

        try:
            position = 0
            # Navigate through the field-token map, and create posting.
            for field, tokens in (document_tokens or {}).items():
                weight = field_weights.get(field, 1.0)
                for token in tokens or []:
                    posting = postings[token]
                    posting["term_frequency"] += 1
                    posting["positions"].append(position)
                    posting["fields"].add(field)
                    posting["score"] += weight / (1 + (position / 1000))
                    position += 1

            # Merge the postings.
            result = {term: {"term_frequency": posting["term_frequency"], "positions": posting["positions"], "fields": sorted(
                posting["fields"]), "score": round(posting["score"], 6)} for term, posting in postings.items()}
            self.logger.info(f"Built postings for {len(result)} terms")
            return result
        except Exception as error:
            self.logger.error(f"Failed to build postings: {error}")
            return {}

    def save_index(self):
        """ This function appends both the document map and inverted index map into the ../data directory as JSON files. It uses the json library 
            to achieve this.
        """
        try:
            # Ensure the data directory exists. If not, create.
            data_directory = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "data"))
            os.makedirs(data_directory, exist_ok=True)

            # Append/write the (document-id:url) map to a file called documents.json.
            with open(os.path.join(data_directory, "documents.json"), "w", encoding="utf-8") as documents_file:
                json.dump(self.documents, documents_file,
                          ensure_ascii=False, indent=2)

            # Append/write the inverted index in memory to a file called index.json.
            with open(os.path.join(data_directory, "index.json"), "w", encoding="utf-8") as index_file:
                json.dump(self.index, index_file, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Saved index and document map to {data_directory}")
        except Exception as error:
            self.logger.error(f"Failed to save index: {error}")

    def load_index(self):
        """ This function loads both the document map and inverted index map from the ../data directory into the indexer class instance variables. It uses
            the json library to achieve this.
        """
        try:
            # Get the paths to the indexer files.
            data_directory = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "data"))
            documents_path = os.path.join(data_directory, "documents.json")
            index_path = os.path.join(data_directory, "index.json")

            # If both files exist, then read them into memory.
            # Otherwise, initalise the indexer field variables as empty python dictionaries.
            if os.path.exists(documents_path):
                with open(documents_path, "r", encoding="utf-8") as documents_file:
                    self.documents = json.load(documents_file)
            else:
                self.documents = {}
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as index_file:
                    self.index = json.load(index_file)
            else:
                self.index = {}

            self.logger.info(
                f"Loaded index and document map from {data_directory}")
        except Exception as error:
            self.logger.error(f"Failed to load index: {error}")
            self.documents = {}
            self.index = {}
