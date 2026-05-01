import math
from concurrent.futures import ThreadPoolExecutor
from indexer import Indexer

# To implement the search functionality, we used the lecture slides to write function stubs and
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


class Search:
    def __init__(self, logger, max_documents_returned=10, indexer=None):

        # The maximum number of documents returned by a search.
        self.max_documents_returned = max_documents_returned

        # Logger.
        self.logger = logger

        self.indexer = indexer or Indexer(logger)
        if indexer is None:
            self.indexer.load_index()

    def search(self, query):
        """ This function takes a user search query, and returns a list of webpages that are most relevant for 
            that query. It utilises the following functions:
            1. tokenise_query: To tokenise the user query.
            2. search_index: To search the index. (Note that this is in the Index class).
            3. score_document: To get a score for each document. (Hence it uses document-at-a-time scoring).
            4. get_url_for_document: To get the URL for a document with a given ID.

            Upon getting a score for each document, this function calculates the Term-frequency Inverse-Document-
            Frequency (TFIDF) for each document, and return the top k results (where k is the class variable max_
            documents_returned).

            To optimise search speed, it uses multithreading to score documents concurrently.

            Args:
                query (str): The search query.

            Returns:
                list: A list of web page URLs that match the search query.
        """
        try:
            tokenised_query = self.tokenise_query(query)
            if not tokenised_query:
                self.logger.warning(
                    "Cannot search because query produced no tokens")
                return []

            matching_postings = self.search_index(tokenised_query)
            if not matching_postings:
                self.logger.info("No search results found")
                return []

            with ThreadPoolExecutor(max_workers=min(len(matching_postings), 8) or 1) as executor:
                scored_documents = list(executor.map(lambda item: (item[0], self.score_document(
                    tokenised_query, item[1])), matching_postings.items()))

            ranked_documents = sorted(
                scored_documents, key=lambda item: item[1], reverse=True)
            urls = []
            for document_id, score in ranked_documents[:self.max_documents_returned]:
                if score <= 0:
                    continue
                url = self.indexer.get_url_for_document(document_id)
                if url:
                    urls.append(url)

            self.logger.info(f"Search returned {len(urls)} URLs")
            return urls
        except Exception as error:
            self.logger.error(f"Failed to search for query {query}: {error}")
            return []

    def tokenise_query(self, query):
        """ This function takes a user query for a search and creates a 1 element list with the query. It then 
            uses the tokenise_tag_content function in the Indexer to tokenise the query.

            Args:
                query (str): The search query to tokenise.

            Returns:
                list: A list of query tokens.
        """
        try:
            if not query:
                self.logger.warning(
                    "Cannot tokenise query because query is missing")
                return []
            tokens = self.indexer.tokenise_tag_content([query])
            self.logger.info(f"Tokenised query into {len(tokens)} tokens")
            return tokens
        except Exception as error:
            self.logger.error(f"Failed to tokenise query {query}: {error}")
            return []

    def search_index(self, query_token):
        """ This function searches the inverted index for postings that match ALL tokens in the query.
            For efficiency, this function uses skip-pointers; alongside multithreading. It makes use of 
            the getter function for the inverted index in the Indexer class.

            Args:
                query_token (list): A list of search query tokens
            Returns:
                dict: Postings within the inverted index that match the query tokens.
        """
        try:
            query_tokens = list(dict.fromkeys(query_token or []))
            if not query_tokens:
                self.logger.warning(
                    "Cannot search index because query tokens are missing")
                return {}

            with ThreadPoolExecutor(max_workers=min(len(query_tokens), 8) or 1) as executor:
                term_indexes = list(executor.map(
                    self.indexer.get_inverted_index, query_tokens))

            if any(not term_index for term_index in term_indexes):
                self.logger.info(
                    "No matching postings found for all query tokens")
                return {}

            ordered_indexes = sorted(term_indexes, key=len)
            matching_document_ids = sorted(
                ordered_indexes[0].keys(), key=self._document_sort_key)

            for term_index in ordered_indexes[1:]:
                other_document_ids = sorted(
                    term_index.keys(), key=self._document_sort_key)
                matching_document_ids = self._intersect_document_ids(
                    matching_document_ids, other_document_ids)
                if not matching_document_ids:
                    self.logger.info("No documents matched all query tokens")
                    return {}

            results = {document_id: {}
                       for document_id in matching_document_ids}
            for token, term_index in zip(query_tokens, term_indexes):
                for document_id in matching_document_ids:
                    results[document_id][token] = term_index[document_id]

            self.logger.info(
                f"Found {len(results)} documents matching all query tokens")
            return results
        except Exception as error:
            self.logger.error(f"Failed to search index: {error}")
            return {}

    def _intersect_document_ids(self, left_document_ids, right_document_ids):
        try:
            matches = []
            left_index = 0
            right_index = 0
            left_skip = int(len(left_document_ids) ** 0.5) or 1
            right_skip = int(len(right_document_ids) ** 0.5) or 1

            while left_index < len(left_document_ids) and right_index < len(right_document_ids):
                left_id = left_document_ids[left_index]
                right_id = right_document_ids[right_index]
                left_key = self._document_sort_key(left_id)
                right_key = self._document_sort_key(right_id)

                if left_key == right_key:
                    matches.append(left_id)
                    left_index += 1
                    right_index += 1
                elif left_key < right_key:
                    next_left_index = left_index + left_skip
                    if next_left_index < len(left_document_ids) and self._document_sort_key(left_document_ids[next_left_index]) <= right_key:
                        left_index = next_left_index
                    else:
                        left_index += 1
                else:
                    next_right_index = right_index + right_skip
                    if next_right_index < len(right_document_ids) and self._document_sort_key(right_document_ids[next_right_index]) <= left_key:
                        right_index = next_right_index
                    else:
                        right_index += 1

            return matches
        except Exception as error:
            self.logger.error(f"Failed to intersect document ids: {error}")
            return []

    def _document_sort_key(self, document_id):
        try:
            return int(document_id)
        except (TypeError, ValueError):
            return str(document_id)

    def score_document(self, tokenised_query, posting):
        """ This function takes a posting for a document and assigns it a score based on it's relevance for the given query. 
            It uses the topical features of the document to create this score..

            Args:
                tokenised_query (str): The tokenised search query to score documents against.
                posting (dict): The document posting to be scored.
        """
        try:
            if not tokenised_query or not posting:
                return 0.0

            total_documents = max(len(self.indexer.documents), 1)
            score = 0.0

            for token in tokenised_query:
                term_posting = posting.get(token)
                if not term_posting:
                    continue

                document_frequency = max(
                    len(self.indexer.get_inverted_index(token)), 1)
                inverse_document_frequency = math.log(
                    (total_documents + 1) / document_frequency) + 1
                term_frequency = term_posting.get("term_frequency", 0)
                topical_score = term_posting.get("score", 0.0)
                score += (term_frequency *
                          inverse_document_frequency) + topical_score

            return round(score, 6)
        except Exception as error:
            self.logger.error(f"Failed to score document: {error}")
            return 0.0
