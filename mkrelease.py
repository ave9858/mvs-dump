#!/usr/bin/env python

import sqlite3
from mvs.mvs import MVS
from mvs_dump import parse_product, db_add_product

from secret import set_secret, get_secret


def get_session() -> MVS:
    """Get MVS session from saved cookie or fall back to getting a fresh one"""
    from get_cookie import get_token

    try:
        print('Trying saved cookie..')

        return MVS(get_secret('cookie'))

    except Exception as e:
        print('Getting new cookie..')
        token = get_token(get_secret('email'), get_secret('password'))

        # overwrite stale cookie with new one
        set_secret('cookie', token)

        return MVS(token)


def publish_update(db_path: str, changed_products: list[tuple[int, str]]) -> None:
    """Publishes an update on GitHub"""

    import gzip
    import os
    import requests

    from datetime import datetime

    # Compress database
    with gzip.open(db_path + '.gz', 'wb') as f:
        c = open(db_path, 'rb').read()
        f.write(c)

    stat_db = os.stat(db_path)

    # Create release
    date = datetime.now()
    tag = f'{date.year:04}-{date.month:02}-{date.day:02}_{date.hour:02}'

    body = "New files for these products:\n```"
    for product in changed_products:
        body += f'\n{product[0]}|{product[1]}'
    body += f'\n```\nUncompressed size: `{(stat_db.st_size + 512*1024) // 1024**2} MiB ({stat_db.st_size // 1024} KiB)`'

    pub_req = requests.post(
        'https://api.github.com/repos/awuctl/mvs-dump/releases',
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {get_secret("github-key")}',
            'X-GitHub-Api-Version': '2022-11-28'
        },
        json={
            'tag_name': tag,
            'target_commitish': 'master',
            'name': tag,
            'body': body
        }
    ).json()

    attach_req = requests.post(
        pub_req['upload_url'].replace('{?name,label}', f'?name={tag}.gz'),
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {get_secret("github-key")}',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/octet-stream'
        },
        data=open(db_path + '.gz', 'rb').read()
    )


def get_file_ids(db: sqlite3.Connection) -> set:
    """Returns the set of file IDs present in the database"""
    with db:
        return set([e[0] for e in db.execute('SELECT id FROM files').fetchall()])


def update_database(db: sqlite3.Connection, count: int) -> None:
    """Updates a given database with a query up to the [count] product ID"""

    mvs_session = get_session()

    response = mvs_session.get_products(list(range(1, count + 1)))
    response = list(response.values())

    with db:
        for product in [parse_product(x) for x in response]:
            db_add_product(db, product)


def get_product_info(db: sqlite3.Connection, id: int) -> tuple[int, str]:

    product_name: str
    with db:
        product_name = db.execute(
            'SELECT name FROM products WHERE id = ?', id).fetchone()[0]

    return id, product_name


def get_products_for_file_ids(db: sqlite3.Connection, ids: list[int]) -> list[tuple[int, str]]:
    """Given a list of file IDs, return the list of products (tuple(id, name)) they belong to"""

    products: list[tuple[int, str]]
    with db:
        products = db.execute(f'''
        SELECT id, name
        FROM products
        WHERE id IN (
            SELECT DISTINCT product
            FROM files
            WHERE id IN (
                { ','.join(['?'] * len(ids)) }
            )
        )''', ids).fetchall()

    return products


def main(db_path: str, count: int, publish: bool) -> None:

    db = sqlite3.connect(db_path)

    old_ids = get_file_ids(db)
    update_database(db, count)
    new_ids = get_file_ids(db)

    if old_ids == new_ids:
        print('[I] Nothing changed.')
        return

    print('[I] Something new detected.')
    changed_products = get_products_for_file_ids(
        db, list(new_ids.difference(old_ids)))

    if publish:
        publish_update(db_path, changed_products)
    else:
        # If not publishing, print what changed.
        print()
        print('[S] Changes found in products:')
        for p in changed_products:
            print(f'[S] {p[0]:5} {p[1]}')

    db.close()


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('database', type=str)
    p.add_argument(
        '--publish', action=argparse.BooleanOptionalAction, default=False)
    p.add_argument('count', type=int, default=15000, nargs='?')

    args = p.parse_args()

    main(args.database, args.count, args.publish)
