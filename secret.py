#!/usr/bin/env python

def get_secret(name: str) -> str:
    with open('secrets/' + name) as secret:
        return secret.read().strip()

def set_secret(name: str, val: str) -> None:
    with open('secrets/' + name) as secret:
        secret.write(val)