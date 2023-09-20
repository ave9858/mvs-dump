#!/usr/bin/env python3
import sqlite3


def reduce_file_list(files: list[dict]) -> list[dict]:
    """
    This reduces a unique file's different-language entries into a single entry with
    comma-separated language codes.
    As of now, this has no use other than to make "(id, file_id) duplicates" disappear.

    Example:
    turns "files":
        (name: "mu_some_file.iso", langc: "pl")
        (name: "mu_some_file.iso", langc: "en")
        (name: "mu_some_file.iso", langc: "zh")
    into:
        (name: "mu_some_file.iso", langc:"pl,en,zh")
    """
    file_dict: dict[tuple[str, str], dict] = {}
    for f in files:
        identity = (f["productId"], f["fileId"])
        if identity in file_dict:
            file_dict[identity]["languageCode"] += "," + f["languageCode"]
        else:
            file_dict[identity] = f
    return list(file_dict.values())


def parse_file(file_entry: dict) -> tuple[int, str, str, str, str, int, int]:
    """Parses file entry into tuple of id, name, desc, lang code, bootstrap link, sha1, sha2"""
    return (
        file_entry["fileId"],
        file_entry["fileName"],
        file_entry["fileDescription"],
        file_entry["languageCode"],
        file_entry["bootstrapperDownloadLink"],
        file_entry["sha1"]
        if "sha1" in file_entry
        and file_entry["sha1"]
        and not file_entry["bootstrapperDownloadLink"]
        else None,
        file_entry["sha256"]
        if "sha256" in file_entry
        and file_entry["sha256"]
        and not file_entry["bootstrapperDownloadLink"]
        else None,
    )


def db_add_product(db: sqlite3.Connection, product: tuple[int, str, list]):
    # Add or skip adding existing product entry
    db.execute(
        """
    insert or ignore into products (id, name) values (?, ?)
    """,
        product[:2],
    )

    # Insert all files for products
    db.executemany(
        """
    insert or ignore into files (product, id, name, desc, langc, bootstrap, sha1, sha2)
    values (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        ((product[0], *file) for file in product[2]),
    )
