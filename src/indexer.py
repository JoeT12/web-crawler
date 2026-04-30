import json

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
    def __init__(self):
        # Inverted index.
        self.index = {}

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

    
    def map_content_to_tag_families(self, parsed_document):
        """ This function takes a document parsed with BeautifulSoup, and creates a map of the content corresponding to a particular tag
            family in the document. For example, if the document has multiple headings, all such heading should be stored as a list under
            the headings key of the map.

            Args:
                parsed_document (BeautifulSoup): The parsed web page.

            Returns:
                dict: A map of HTML tag families to document contents.
        """

    def tokenise_tag_content(self, tag_content):
        """ This function takes a list of content that was enclosed within a family of HTML tags for a particular document, and tokenises it into individual terms.
            It handles: small words, hyphens, apostrophes and stop words carefully, disposing of them if they offer no additional meaning to the surrounding terms. It
            also stems words to using the porter stemmer to improve searching efficiency within the index and reducing the number of forms needed to be stored in the index.
            In addition, it should also detect phrases and n-grams using the part-of-speech tagging.

            Args:
                tag_content (list): A map of HTML tag families to document contents.

            Returns:
                list: A tokenised version of the list provided.
        """        

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

    def save_index(self):
        """ This function appends both the document map and inverted index map into the ../data directory as JSON files. It uses the json library 
            to achieve this.
        """

    def load_index(self):
        """ This function loads both the document map and inverted index map from the ../data directory into the indexer class instance variables. It uses
            the json library to achieve this.
        """        
