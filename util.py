import os
import logging
from typing import List


def get_tokens(token_file: str) -> List[str]:
    if not os.path.exists(token_file):
        logging.error("Please put GitHub Tokens in {} for this script to work".format(token_file))
        return []
    with open(token_file, "r") as f:
        return list(x.strip() for x in f.readlines())
