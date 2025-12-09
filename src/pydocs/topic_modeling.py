#!/usr/bin/env python3
"""
Topic Modeling Script using Gensim

This script performs topic modeling on a corpus of text documents using Latent Dirichlet Allocation (LDA).
It preprocesses the text, creates a document-term matrix, and extracts topics using Gensim.

Usage:
    python topic_modeling.py --input_dir <path_to_documents> --num_topics <number_of_topics>
"""

import os
import argparse
import logging
from typing import List, Tuple
import glob
from pathlib import Path

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

from gensim import corpora
from gensim.models import LdaModel
from gensim.parsing.preprocessing import (
    preprocess_string,
    strip_tags,
    strip_punctuation,
    strip_multiple_whitespaces,
    strip_numeric,
    remove_stopwords,
    strip_short,
    stem_text,
)

import pandas as pd

# Download required NLTK data
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")

try:
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("wordnet")


# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TopicModeler:
    """A class to perform topic modeling on text documents."""

    def __init__(self, language="english"):
        """
        Initialize the TopicModeler.

        Args:
            language (str): Language for stopwords and tokenization
        """
        self.language = language
        self.stop_words = set(stopwords.words(language))
        self.lemmatizer = WordNetLemmatizer()
        self.documents = []
        self.processed_docs = []
        self.dictionary = None
        self.corpus = None
        self.lda_model = None

    def load_documents(self, input_path: str) -> None:
        """
        Load documents from a directory or file.

        Args:
            input_path (str): Path to directory containing text files or a single file
        """
        logger.info(f"Loading documents from {input_path}")

        path = Path(input_path)

        if path.is_file():
            # Single file
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                self.documents = [content]
        elif path.is_dir():
            # Directory of files
            file_patterns = ["*.txt", "*.md", "*.html", "*.htm"]
            files = []
            for pattern in file_patterns:
                files.extend(glob.glob(str(path / "**" / pattern), recursive=True))

            logger.info(f"Found {len(files)} files")

            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        self.documents.append(content)
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")
        else:
            raise ValueError(
                f"Input path {input_path} is neither a file nor a directory"
            )

        logger.info(f"Loaded {len(self.documents)} documents")

    def preprocess_documents(self, custom_filters: List[str] = None) -> None:
        """
        Preprocess documents for topic modeling.

        Args:
            custom_filters (List[str]): Custom list of words to filter out
        """
        logger.info("Preprocessing documents")

        # Default Gensim filters
        default_filters = [
            strip_tags,
            strip_punctuation,
            strip_multiple_whitespaces,
            strip_numeric,
            remove_stopwords,
            strip_short,
            stem_text,
        ]

        # Add custom filters if provided
        if custom_filters:
            # Create a custom filter function
            def custom_remove_words(s):
                for word in custom_filters:
                    s = s.replace(word, "")
                return s

            default_filters.append(custom_remove_words)

        # Process each document
        self.processed_docs = []
        for doc in self.documents:
            # Apply Gensim preprocessing
            processed = preprocess_string(doc, default_filters)
            self.processed_docs.append(processed)

        logger.info(f"Preprocessed {len(self.processed_docs)} documents")

    def create_dictionary_and_corpus(self) -> None:
        """Create dictionary and corpus for LDA."""
        logger.info("Creating dictionary and corpus")

        # Create dictionary
        self.dictionary = corpora.Dictionary(self.processed_docs)

        # Filter extremes (optional)
        self.dictionary.filter_extremes(no_below=2, no_above=0.8)

        # Create corpus
        self.corpus = [self.dictionary.doc2bow(doc) for doc in self.processed_docs]

        logger.info(f"Dictionary size: {len(self.dictionary)}")
        logger.info(f"Corpus size: {len(self.corpus)}")

    def train_lda_model(
        self,
        num_topics: int = 10,
        passes: int = 10,
        alpha: str = "auto",
        eta: str = "auto",
    ) -> None:
        """
        Train the LDA model.

        Args:
            num_topics (int): Number of topics to extract
            passes (int): Number of passes through the corpus
            alpha (str): Document-topic density parameter
            eta (str): Topic-word density parameter
        """
        logger.info(f"Training LDA model with {num_topics} topics")

        if not self.corpus or not self.dictionary:
            raise ValueError(
                "Dictionary and corpus must be created before training the model"
            )

        # Train LDA model
        self.lda_model = LdaModel(
            corpus=self.corpus,
            id2word=self.dictionary,
            num_topics=num_topics,
            passes=passes,
            alpha=alpha,
            eta=eta,
            random_state=42,
        )

        logger.info("LDA model training completed")

    def get_topics(
        self, num_words: int = 10
    ) -> List[Tuple[int, List[Tuple[str, float]]]]:
        """
        Get the topics from the trained model.

        Args:
            num_words (int): Number of words to show per topic

        Returns:
            List of topics with their words and probabilities
        """
        if not self.lda_model:
            raise ValueError("Model must be trained before getting topics")

        topics = self.lda_model.print_topics(num_words=num_words)
        return [
            (topic_id, self.lda_model.show_topic(topic_id, num_words))
            for topic_id in range(self.lda_model.num_topics)
        ]

    def print_topics(self, num_words: int = 10) -> None:
        """
        Print the topics in a readable format.

        Args:
            num_words (int): Number of words to show per topic
        """
        if not self.lda_model:
            raise ValueError("Model must be trained before printing topics")

        topics = self.get_topics(num_words)

        print("\n" + "=" * 50)
        print("TOPICS IDENTIFIED")
        print("=" * 50)

        for topic_id, words in topics:
            print(f"\nTopic {topic_id + 1}:")
            for word, prob in words:
                print(f"  {word}: {prob:.4f}")

    def get_document_topics(self, doc_index: int) -> List[Tuple[int, float]]:
        """
        Get topic distribution for a specific document.

        Args:
            doc_index (int): Index of the document

        Returns:
            List of (topic_id, probability) tuples
        """
        if not self.lda_model or not self.corpus:
            raise ValueError(
                "Model and corpus must be trained before getting document topics"
            )

        if doc_index >= len(self.corpus):
            raise ValueError(f"Document index {doc_index} out of range")

        return self.lda_model.get_document_topics(self.corpus[doc_index])

    def save_model(self, filepath: str) -> None:
        """
        Save the trained model to disk.

        Args:
            filepath (str): Path to save the model
        """
        if not self.lda_model:
            raise ValueError("Model must be trained before saving")

        self.lda_model.save(filepath)
        logger.info(f"Model saved to {filepath}")

    def save_topics_to_csv(self, filepath: str, num_words: int = 10) -> None:
        """
        Save topics to a CSV file.

        Args:
            filepath (str): Path to save the CSV
            num_words (int): Number of words per topic
        """
        if not self.lda_model:
            raise ValueError("Model must be trained before saving topics")

        topics = self.get_topics(num_words)

        # Prepare data for DataFrame
        data = []
        for topic_id, words in topics:
            row = {"topic_id": topic_id + 1}
            for i, (word, prob) in enumerate(words):
                row[f"word_{i + 1}"] = word
                row[f"prob_{i + 1}"] = prob
            data.append(row)

        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        logger.info(f"Topics saved to {filepath}")


def main():
    """Main function to run topic modeling."""
    parser = argparse.ArgumentParser(
        description="Perform topic modeling on text documents"
    )
    parser.add_argument(
        "--input_dir", required=True, help="Path to directory containing text files"
    )
    parser.add_argument(
        "--num_topics",
        type=int,
        default=10,
        help="Number of topics to extract (default: 10)",
    )
    parser.add_argument(
        "--num_words",
        type=int,
        default=10,
        help="Number of words per topic (default: 10)",
    )
    parser.add_argument(
        "--passes",
        type=int,
        default=10,
        help="Number of passes through the corpus (default: 10)",
    )
    parser.add_argument(
        "--output_dir",
        default="output",
        help="Output directory for results (default: output)",
    )
    parser.add_argument(
        "--save_model", action="store_true", help="Save the trained model"
    )

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize topic modeler
    modeler = TopicModeler()

    try:
        # Load documents
        modeler.load_documents(args.input_dir)

        if len(modeler.documents) == 0:
            logger.error("No documents found. Exiting.")
            return

        # Preprocess documents
        modeler.preprocess_documents()

        # Create dictionary and corpus
        modeler.create_dictionary_and_corpus()

        # Train LDA model
        modeler.train_lda_model(num_topics=args.num_topics, passes=args.passes)

        # Print topics
        modeler.print_topics(args.num_words)

        # Save topics to CSV
        topics_csv = os.path.join(args.output_dir, "topics.csv")
        modeler.save_topics_to_csv(topics_csv, args.num_words)
        logger.info(f"Topics saved to {topics_csv}")

        # Save model if requested
        if args.save_model:
            model_path = os.path.join(args.output_dir, "lda_model")
            modeler.save_model(model_path)
            logger.info(f"Model saved to {model_path}")

        logger.info("Topic modeling completed successfully!")

    except Exception as e:
        logger.error(f"Error during topic modeling: {e}")
        raise


if __name__ == "__main__":
    main()
