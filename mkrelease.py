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


def publish_update(db_path: str, new_file_ids: list) -> None:
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

    db = sqlite3.connect(db_path)
    r = db.execute(f'''
    SELECT id, name
    FROM products
    WHERE id IN (
        SELECT DISTINCT product
        FROM files
        WHERE id IN ({','.join(['?']*len(new_file_ids))})
    )
    ''', new_file_ids)

    # Create release
    date = datetime.now()
    tag = f'{date.year:04}-{date.month:02}-{date.day:02}_{date.hour:02}'

    body = "New files for these products:\n```"
    for x in r:
        body += f'\n{x[0]}|{x[1]}'
    body += f'\n```\nUncompressed size: `{stat_db.st_size // 1024**2} MiB ({stat_db.st_size // 1024} KiB)`'

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


def main(db_path: str, count: int, publish: bool) -> None:

    db = sqlite3.connect(db_path)

    # check old file ids
    old_ids = set([e[0] for e in db.execute(
        'SELECT id FROM files').fetchall()])

    mvs_session = get_session()

    response = mvs_session.get_products(list(range(1, count + 1)))
    response = list(response.values())

    for product in [parse_product(x) for x in response]:
        db_add_product(db.cursor(), product)

    # check updated file ids
    new_ids = set([e[0] for e in db.execute(
        'SELECT id FROM files').fetchall()])

    db.commit()
    db.close()

    # new_ids can only be bigger
    if old_ids == new_ids:
        print('[I] Nothing new detected.')
        return

    print('[I] Something new detected.')
    if publish:
        publish_update(db_path, list(new_ids.difference(old_ids)))


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('database', type=str)
    p.add_argument('--publish', action=argparse.BooleanOptionalAction, default=False)
    p.add_argument('count', type=int, default=15000, nargs='?')

    args = p.parse_args()

    main(args.database, args.count, args.publish)
