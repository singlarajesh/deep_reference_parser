#!/usr/bin/env python3
# coding: utf-8

import os
from logging import getLogger
from urllib import parse, request

from .logger import logger
from .__version__ import __model_version__

def get_path(path):
    return os.path.join(
        os.path.dirname(__file__),
        path
    )

LATEST_CFG = get_path(f'configs/{__model_version__}.ini')

def download_model_artefact(artefact, s3_slug):
    """ Checks if model artefact exists and downloads if not

    Args:
        artefact (str): File to be downloaded
        s3_slug (str): http uri to latest model dir on s3, e.g.:
        https://datalabs-public.s3.eu-west-2.amazonaws.com/deep_reference_parser
        /models/latest
    """

    path, _ = os.path.split(artefact)
    os.makedirs(path, exist_ok=True)

    if os.path.exists(artefact):
        logger.debug(f"{artefact} exists, nothing to be done...")
    else:
        logger.debug("Could not find %s. Downloading...", artefact)

        url = parse.urljoin(s3_slug, artefact)

        request.urlretrieve(url, artefact)

def download_model_artefacts(model_dir, s3_slug, artefacts=None):
    """
    """

    if not artefacts:

        artefacts = [
            "char2ind.pickle", "ind2label.pickle", "ind2word.pickle",
            "label2ind.pickle", "maxes.pickle", "weights.h5", 
            "word2ind.pickle"
        ]

    for artefact in artefacts:
        artefact = os.path.join(model_dir, artefact)
        download_model_artefact(artefact, s3_slug)
