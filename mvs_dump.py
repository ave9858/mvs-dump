#!/usr/bin/env python

from functools import reduce
from mvs.mvs import MVS
import sqlite3
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


def parse_file(file_entry: dict) -> tuple[int, str, str, str, str, int, int]:
    """Parses file entry into tuple of id, name, desc, lang code, bootstrap link, sha1, sha2"""
    return (
        file_entry['id'],
        file_entry['fileName'],
        file_entry['fileDescription'],
        file_entry['languageCode'],
        file_entry['bootstrapperDownloadLink'],
        file_entry['sha1'] if 'sha1' in file_entry and file_entry['sha1'] and not file_entry['bootstrapperDownloadLink'] else None,
        file_entry['sha256'] if 'sha256' in file_entry and file_entry['sha256'] and not file_entry['bootstrapperDownloadLink'] else None
    )


def parse_product(product_entry: dict) -> tuple[int, str, list]:
    id = product_entry['productId']

    # the name is part of the file's info for some reason
    names = list(set([f['productName']
                 for f in product_entry['fileDetailModels']]))
    if len(names) > 1:
        print(f'Product naming inconsistency for product {id}: {names}')

    product_entry['fileDetailModels'] = reduce_file_list(
        product_entry['fileDetailModels'])

    files = list(map(parse_file, product_entry['fileDetailModels']))
    return (id, names[0], files)


def db_add_product(cursor: sqlite3.Cursor, product: tuple[int, str, list]):
    # Add or skip adding existing product entry
    cursor.execute('''
    insert or ignore into products (id, name) values (?, ?)
    ''', product[:2])

    # Insert all files for products
    cursor.executemany('''
    insert or ignore into files (product, id, name, desc, langc, bootstrap, sha1, sha2)
    values (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ((product[0], *file) for file in product[2]))


if __name__ == '__main__':

    import argparse

    ap = argparse.ArgumentParser(prog='mvs-dump')
    ap.add_argument('file',  help='Destination database file')
    ap.add_argument(
        'count', help='Number of consecutive IDs to query for', type=int)
    ap.add_argument('-c', type=argparse.FileType('r'),
                    dest='cookie', help='Cookie file', default='mvs.cookie')

    args = ap.parse_args()

    mvs = MVS(args.cookie.read().strip())
    db = sqlite3.connect(args.file)

    mvs_response = mvs.get_products(list(range(1, args.count + 1)))
    products = map(parse_product, list(mvs_response.values()))

    for p in products:
        db_add_product(db.cursor(), p)

    db.commit()
    db.close()
