#!/usr/bin/env python3
# coding: utf-8

"""
Class used in scripts/prodigy_to_tsv.py which converts token annotated jsonl
files to tab-separated-values files for use in the deep reference parser
"""

import csv
import re
import sys
from functools import reduce

import numpy as np
import plac
from wasabi import Printer, table

from ..io import read_jsonl
from ..logger import logger

msg = Printer()


class TokenLabelPairs:
    """
    Convert prodigy format docs or list of lists into tuples of (token, label).
    """

    def __init__(
        self, line_limit=250, respect_line_endings=False, respect_doc_endings=True
    ):
        """
        Args:
            line_limit(int): Maximum number of tokens allowed per training
                example. If you are planning to use this data for making
                predictions, then this should correspond to the max_words
                attribute for the DeepReferenceParser class used to train the
                model.
            respect_line_endings(bool): If true, line endings appearing in the
                text will be respected, leading to much shorter line lengths
                usually <10. Typically this results in a much worser performing
                model, but follows the convention set by Rodrigues et al.
            respect_doc_endings(bool): If true, a line ending is added at the
                end of each document. If false, then the end of a document flows
                into the beginning of the next document.
        """

        self.line_count = 0
        self.line_lengths = []
        self.line_limit = line_limit
        self.respect_doc_endings = respect_doc_endings
        self.respect_line_endings = respect_line_endings

    def run(self, docs):
        """
        """

        out = []

        for doc in docs:
            out.extend(self.yield_token_label_pair(doc))

        self.stats(out)

        return out

    def stats(self, out):

        avg_line_len = np.round(np.mean(self.line_lengths), 2)

        logger.debug("Returning %s examples", self.line_count)
        logger.debug("Average line length: %s", avg_line_len)

    def yield_token_label_pair(self, doc, lists=False):
        """
        Expect list of jsons loaded from a jsonl

        Args:
            doc (dict): Document in prodigy format or list of lists
            lists (bool): Expect a list of lists rather than a prodigy format
                dict?

        NOTE: Makes the assumption that every token has been labelled in spans. This
        assumption will be true if the data has been labelled with prodigy, then
        spans covering entire references have been converted to token spans. OR that
        there are no spans at all, and this is being used to prepare data for
        prediction.
        """

        # Ensure that spans and tokens are sorted (they should be)

        if lists:
            tokens = doc
        else:
            tokens = sorted(doc["tokens"], key=lambda k: k["id"])

        # For prediction, documents may not yet have spans. If they do, sort
        # them too based on token_start which is equivalent to id in
        # doc["tokens"].

        spans = doc.get("spans")

        if spans:
            spans = sorted(doc["spans"], key=lambda k: k["token_start"])

        # Set a token counter that is used to limit the number of tokens to
        # line_limit.

        token_counter = int(0)

        doc_len = len(tokens)

        for i, token in enumerate(tokens, 1):

            label = None

            # For case when tokens have been labelled with spans (for training
            # data).

            if spans:
                # Need to remove one from index as it starts at 1!
                label = spans[i - 1].get("label")

            text = token["text"]

            # If the token is empty even if it has been labelled, pass it

            if text == "":

                pass

            # If the token is a newline (and possibly other characters) and we want
            # to respect line endings in the text, then yield a (None, None) tuple
            # which will be converted to a blank line when the resulting tsv file
            # is read.

            elif re.search(r"\n", text) and self.respect_line_endings:

                # Is it blank after whitespace is removed?

                if text.strip() == "":

                    yield (None, None)

                self.line_lengths.append(token_counter)
                self.line_count += 1

                token_counter = 0

            elif token_counter == self.line_limit:

                # Yield None, None to signify a line ending, then yield the next
                # token.

                yield (None, None)
                yield (text.strip(), label)

                # Set to one to account for the first token being added.

                self.line_lengths.append(token_counter)
                self.line_count += 1

                token_counter = 1

            elif i == doc_len and self.respect_doc_endings:

                # Case when the end of the document has been reached, but it is
                # less than self.lime_limit. This assumes that we want to retain
                # a line ending which denotes the end of a document, and the
                # start of new one.

                yield (text.strip(), label)
                yield (None, None)

                self.line_lengths.append(token_counter)
                self.line_count += 1

            else:

                # Returned the stripped label.

                yield (text.strip(), label)

                token_counter += 1


def get_document_hashes(dataset):
    """Get the hashes for every doc in a dataset and return as set
    """
    return set([doc["_input_hash"] for doc in dataset])


def check_all_equal(lst):
    """Check that all items in a list are equal and return True or False
    """
    return not lst or lst.count(lst[0]) == len(lst)


def hash_matches(doc, hash):
    """Check whether the hash of the passed doc matches the passed hash
    """
    return doc["_input_hash"] == hash


def get_doc_by_hash(dataset, hash):
    """Return a doc from a dataset where hash matches doc["_input_hash"]
    Assumes there will only be one match!
    """
    return [doc for doc in dataset if doc["_input_hash"] == hash][0]


def get_tokens(doc):
    return [token["text"] for token in doc["tokens"]]


def check_inputs(annotated_data):
    """Checks whether two prodigy datasets contain the same docs (evaluated by
    doc["_input_hash"] and whether those docs contain the same tokens. This is
    essential to ensure that two independently labelled datasets are compatible.
    If they are not, an error is raised with an informative errors message.

    Args:
        annotated_data (list): List of datasets in prodigy format that have
        been labelled with token level spans. Hence len(tokens)==len(spans).
    """

    doc_hashes = list(map(get_document_hashes, annotated_data))

    # Check whether there are the same docs between datasets, and if
    # not return information on which ones are missing.

    if not check_all_equal(doc_hashes):
        msg.fail("Some documents missing from one of the input datasets")

        for i in range(len(doc_hashes)):
            for j in range(i + 1, len(doc_hashes)):
                diff = set(doc_hashes[i]) ^ set(doc_hashes[j])

                if diff:
                    msg.fail(
                        f"Docs {diff} unequal between dataset {i} and {j}", exits=1
                    )

    # Check that the tokens between the splitting and parsing docs match

    for hash in doc_hashes[0]:

        hash_matches = list(map(lambda x: get_doc_by_hash(x, hash), annotated_data))
        tokens = list(map(get_tokens, hash_matches))

        if not check_all_equal(tokens):
            msg.fail(f"Token mismatch for document {hash}", exits=1)

    return True


def sort_docs_list(lst):
    """Sort a list of prodigy docs by input hash
    """
    return sorted(lst, key=lambda k: k["_input_hash"])


def combine_token_label_pairs(pairs):
    """Combines a list of [(token, label), (token, label)] to give
    (token,label,label).
    """
    return pairs[0][0:] + tuple(pair[1] for pair in pairs[1:])


@plac.annotations(
    input_files=(
        "Comma separated list of paths to jsonl files containing prodigy docs.",
        "positional",
        None,
        str,
    ),
    output_file=("Path to output tsv file.", "positional", None, str),
    respect_lines=(
        "Respect line endings? Or parse entire document in a single string?",
        "flag",
        "r",
        bool,
    ),
    respect_docs=(
        "Respect doc endings or parse corpus in single string?",
        "flag",
        "d",
        bool,
    ),
    line_limit=("Number of characters to include on a line", "option", "l", int),
)
def prodigy_to_tsv(
    input_files, output_file, respect_lines, respect_docs, line_limit=250
):
    """
    Convert token annotated jsonl to token annotated tsv ready for use in the
    deep_reference_parser model.

    Will combine annotations from two jsonl files containing the same docs and
    the same tokens by comparing the "_input_hash" and token texts. If they are
    compatible, the output file will contain both labels ready for use in a
    multi-task model, for example:

           token   label   label
    ------------   -----   -----
      References   o       o
                   o       o
               1   o       o
               .   o       o
                   o       o
             WHO   title   b-r
       treatment   title   i-r
      guidelines   title   i-r
             for   title   i-r
            drug   title   i-r
               -   title   i-r
       resistant   title   i-r
    tuberculosis   title   i-r
               ,   title   i-r
            2016   title   i-r

    Multiple files must be passed as a comma separated list e.g.

    python -m deep_reference_parser.prodigy prodigy_to_tsv file1.jsonl,file2.jsonl out.tsv

    """

    input_files = input_files.split(",")

    msg.info(f"Loading annotations from {len(input_files)} datasets")
    msg.info(f"Respect line endings: {respect_lines}")
    msg.info(f"Respect doc endings: {respect_docs}")
    msg.info(f"Line limit: {line_limit}")

    # Read the input_files. Note the use of map here, because we don't know
    # how many sets of annotations area being passed in the list. It could be 2
    # but in future it may be more.

    annotated_data = list(map(read_jsonl, input_files))

    # Check that the tokens match between sets of annotations. If not raise
    # errors and stop.

    check_inputs(annotated_data)

    # Sort the docs so that they are in the same order before converting to
    # token label pairs.

    annotated_data = list(map(sort_docs_list, annotated_data))

    tlp = TokenLabelPairs(
        respect_doc_endings=respect_docs,
        respect_line_endings=respect_lines,
        line_limit=line_limit,
    )

    pairs_list = list(map(tlp.run, annotated_data))

    # NOTE: Use of reduce to handle pairs_list of unknown length

    if len(pairs_list) > 1:
        merged_pairs = (
            combine_token_label_pairs(pairs) for pairs in reduce(zip, pairs_list)
        )
        example_pairs = [
            combine_token_label_pairs(pairs)
            for i, pairs in enumerate(reduce(zip, pairs_list))
            if i < 15
        ]
    else:
        merged_pairs = pairs_list[0]
        example_pairs = merged_pairs[0:14]

    with open(output_file, "w") as fb:
        writer = csv.writer(fb, delimiter="\t")
        # Write DOCSTART and a blank line
        # writer.writerows([("DOCSTART", None), (None, None)])
        writer.writerows(merged_pairs)

    # Print out the first ten rows as a sense check

    msg.divider("Example output")
    header = ["token"] + ["label"] * len(annotated_data)
    aligns = ["r"] + ["l"] * len(annotated_data)
    formatted = table(example_pairs, header=header, divider=True, aligns=aligns)
    print(formatted)

    msg.good(f"Wrote token/label pairs to {output_file}")
