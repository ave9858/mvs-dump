#!/usr/bin/env python

from functools import reduce

def reduce_file_list(files: list[dict]) -> list[dict]:
    """
        This reduces a unique file's different-language entries into a single entry with comma-separated language codes.
        As of now, this has no use other than to make "(id, file_id) duplicates" disappear.

        Example:
        turns "files":
            (name: "mu_some_file.iso", langc: "pl")
            (name: "mu_some_file.iso", langc: "en")
            (name: "mu_some_file.iso", langc: "zh")
        into:
            (name: "mu_some_file.iso", langc:"pl,en,zh")
    """
    final, uniques = [], []

    for f in files:
        identity = (f['productId'], f['id']) 
        if identity not in uniques:
            f['languageCode'] = reduce(
                lambda x, y: f"{x},{y['languageCode']}",
                filter(
                    lambda x: (x['productId'], x['id']) == identity,
                    files), '')[1:]
            uniques.append(identity)
            final.append(f)
    return final