#!/usr/bin/env python

from functools import reduce
from mvs.mvs import MVS
import sqlite3
from sanity import reduce_file_list

def parse_file(file_entry: dict) -> tuple[int, str, str, str, str, int, int]:
    """Parses file entry into tuple of id, name, desc, lang code, bootstrap link, sha1, sha2"""
    return (
        file_entry['id'],
        file_entry['fileName'],
        file_entry['fileDescription'],
        file_entry['languageCode'],
        file_entry['bootstrapperDownloadLink'],
        file_entry['sha1']   if 'sha1' in file_entry   and file_entry['sha1']    and not file_entry['bootstrapperDownloadLink'] else None,
        file_entry['sha256'] if 'sha256' in file_entry and  file_entry['sha256'] and not file_entry['bootstrapperDownloadLink'] else None
    )

def parse_product(product_entry: dict) -> tuple[int, str, list]:
    id = product_entry['productId']
    
    # the name is part of the file's info for some reason
    names = list(set([f['productName'] for f in product_entry['fileDetailModels']]))
    if len(names) > 1:
        print(f'Product naming inconsistency for product {id}: {names}')
    
    product_entry['fileDetailModels'] = reduce_file_list(product_entry['fileDetailModels'])

    files = list(map(parse_file, product_entry['fileDetailModels']))
    return (id, names[0], files)

def db_add_product(cursor: sqlite3.Cursor, product: tuple[int, str, list]):
    # Add or skip adding existing product entry
    cursor.execute('''
    insert or ignore into products (id, name) values (?, ?)
    ''', product[:2])

    # Insert all files for products
    # (this will shit the bed on identical files, this is intentional)
    cursor.executemany('''
    insert into files (product, id, name, desc, langc, bootstrap, sha1, sha2)
    values (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ((product[0], *file) for file in product[2]))

if __name__ == '__main__':
    import sys

    if len(sys.argv) == 1:
        mvs = MVS(input('Cookie: '))
        count = int(input('Product count: '))
        db = sqlite3.connect(input('Database file name: '))
    elif len(sys.argv) == 3:
        with open('mvs.cookie') as f:
            mvs = MVS(f.read().strip())
        count = int(sys.argv[1])
        db = sqlite3.connect(sys.argv[2])
    else:
        print('Invalid usage:\nmvs-dump.py <product count> <db file>')

    response = mvs.get_products(list(range(1, count + 1)))
    
    products = map(parse_product, list(response.values()))

    for prod in products:
        db_add_product(db.cursor(), prod)
    db.commit()
    db.close()