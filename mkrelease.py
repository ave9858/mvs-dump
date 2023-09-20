#!/usr/bin/env python3

import argparse
import gzip
import os
import sqlite3
from datetime import datetime
from os import path

import requests

from get_cookie import get_token
from mvs import MVS, CookieExpired
from mvs_dump import db_add_product, parse_file, reduce_file_list
from secret import get_secret, set_secret

BATCH_SIZE = 128


def get_session() -> MVS:
    """Get MVS session from saved cookie or fall back to getting a fresh one"""
    try:
        print("Using saved cookie..")

        return MVS(get_secret("cookie"))

    except (CookieExpired, FileNotFoundError) as e:
        print("Getting new cookie because:", e)
        token = get_token(get_secret("email"), get_secret("password"))

        # overwrite stale cookie with new one
        set_secret("cookie", token)

        return MVS(token)


def publish_update(db_path: str, changed_products: list[tuple[int, str]]) -> None:
    """Publishes an update on GitHub"""

    # Compress database
    with gzip.open(db_path + ".gz", "wb") as g:
        with open(db_path, "rb") as f:
            c = f.read()
        g.write(c)

    stat_db = os.stat(db_path)

    # Create release
    date = datetime.now()
    tag = f"{date.year:04}-{date.month:02}-{date.day:02}_{date.hour:02}"

    body = "New files for these products:\n```"
    for product in changed_products:
        body += f"\n{product[0]}|{product[1]}"
    body += f"\n```\nUncompressed size: `{stat_db.st_size // 1024} KiB`"

    pub_req = requests.post(
        "https://api.github.com/repos/awuctl/mvs-dump/releases",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f'Bearer {get_secret("github-key")}',
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"tag_name": tag, "target_commitish": "master", "name": tag, "body": body},
        timeout=30,
    ).json()

    requests.post(
        pub_req["upload_url"].replace("{?name,label}", f"?name={tag}.gz"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f'Bearer {get_secret("github-key")}',
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/octet-stream",
        },
        data=open(db_path + ".gz", "rb").read(),
        timeout=30,
    )


def get_file_ids(db: sqlite3.Connection) -> set[int]:
    """Returns the set of file IDs present in the database"""
    with db:
        return {e[0] for e in db.execute("SELECT id FROM files").fetchall()}


def get_product_ids(db: sqlite3.Connection) -> set[int]:
    """Returns the set of product IDs present in the database"""
    with db:
        return {e[0] for e in db.execute("SELECT id FROM products").fetchall()}


def get_all_products(db: sqlite3.Connection) -> dict[int, str]:
    with db:
        return dict(db.execute("SELECT id, name FROM products").fetchall())


def get_products_for_file_ids(
    db: sqlite3.Connection, ids: list[int]
) -> list[tuple[int, str]]:
    """Given a list of file IDs, return the list of products (tuple(id, name)) they belong to"""
    products: list[tuple[int, str]]
    with db:
        products = db.execute(
            f"""
        SELECT id, name
        FROM products
        WHERE id IN (
            SELECT DISTINCT product
            FROM files
            WHERE id IN (
                { ','.join(['?'] * len(ids)) }
            )
        )""",
            ids,
        ).fetchall()

    return products


def check_new_products(ids: set[int], mvs_session: MVS) -> list[dict]:
    """Given a list of existing product IDs, check for new products and return data"""
    highest_product_id = max(ids)
    data: list[dict] = []
    start = 1

    while True:
        new = mvs_session.get_products(
            list(
                range(
                    highest_product_id + start, highest_product_id + start + BATCH_SIZE
                )
            )
        )
        if not new:
            break
        data += new.values()
        start += BATCH_SIZE

    return data


def get_all_data(max_id: int, mvs_session: MVS) -> list[dict]:
    data: list[dict] = []

    ids = list(range(max_id + 1))

    chunks = [ids[i : i + BATCH_SIZE] for i in range(0, len(ids), BATCH_SIZE)]

    for chunk in chunks:
        data += mvs_session.get_products(chunk).values()

    return data


def get_new_product_names(mvs_session: MVS) -> dict[int, str]:
    """Get product names for products based on search."""
    search_results = mvs_session.get_search()
    product_dict = {}
    for result in search_results:
        product_dict[result["productId"]] = result["productName"]
    return product_dict


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=str)
    parser.add_argument(
        "--publish", action=argparse.BooleanOptionalAction, default=False
    )

    args = parser.parse_args()

    db_path = path.basename(path.realpath(args.database))

    db = sqlite3.connect(db_path)

    old_product_ids = get_product_ids(db)
    old_file_ids = get_file_ids(db)
    mvs_session = get_session()

    if new_products := check_new_products(old_product_ids, mvs_session):
        new_products += get_all_data(max(old_product_ids), mvs_session)
        id_dict = get_all_products(db) | get_new_product_names(mvs_session)
        for product in new_products:
            product["fileDetailModels"] = reduce_file_list(product["fileDetailModels"])
            files = [parse_file(file) for file in product["fileDetailModels"]]
            db_add_product(
                db, (product["productId"], id_dict[product["productId"]], files)
            )
    else:
        print("[I] No new products, exiting")
        return
    db.commit()
    new_file_ids = get_file_ids(db)
    print("[I] Something new detected.")
    changed_products = get_products_for_file_ids(
        db, list(new_file_ids.difference(old_file_ids))
    )
    db.close()
    if args.publish:
        publish_update(db_path, changed_products)
    else:
        # If not publishing, print what changed.
        print()
        print("[S] Changes found in products:")
        for p in changed_products:
            print(f"[S] {p[0]:5} {p[1]}")


if __name__ == "__main__":
    _main()
