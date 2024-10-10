"""
Functions for Importing and Manipulating Media From a Directory
"""

import pandas as pd
import os

from .media import get_sequence_id

from animl import build_file_manifest


def import_directory(mpDB, directory):
    manifest = build_file_manifest(directory)
    manifest = get_sequence_id(manifest)
    print(manifest)
