
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
    def __init__(self, logger, max_documents_returned=10):

        # The maximum number of documents returned by a search.
        self.max_documents_returned = 10

        # Logger.
        self.logger = logger

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

    def tokenise_query(self, query):
        """ This function takes a user query for a search and creates a 1 element list with the query. It then 
            uses the tokenise_tag_content function in the Indexer to tokenise the query.

            Args:
                query (str): The search query to tokenise.

            Returns:
                list: A list of query tokens.
        """

    def score_document(self, tokenised_query, posting):
        """ This function takes a posting for a document and assigns it a score based on it's relevance for the given query. 
            It uses the topical features of the document to create this score..

            Args:
                tokenised_query (str): The tokenised search query to score documents against.
                posting (dict): The document posting to be scored.
        """
