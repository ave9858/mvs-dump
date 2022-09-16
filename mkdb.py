#!/usr/bin/env python

import sqlite3

if __name__ == '__main__':
    """Running this will initialize an MVS database at file arg1"""
    import sys
    
    if len(sys.argv) < 2:
        print('Usage: mkdb.py <file>')
        exit(1)

    con = sqlite3.connect(sys.argv[1])
    cur = con.cursor()

    cur.execute('pragma case_sensitive_like = false;')
    cur.execute('pragma count_changes = true;')

    cur.execute('''
    create table products (
        id        int      primary key,
        name      varchar
    );
    ''')

    cur.execute('''
    create table files (
        id        int,
        product   int,
        name      varchar,
        desc      varchar,
        langc     varchar,
        bootstrap varchar  default null,
        sha1      varchar  default null,
        sha2      varchar  default null,

        foreign key(product) references products(id),
        primary key(id, product)
    );
    ''')

    con.commit()
    con.close()