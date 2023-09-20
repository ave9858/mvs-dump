def get_secret(name: str) -> str:
    with open(f"secrets/{name}", encoding="utf-8") as secret:
        return secret.read().strip()


def set_secret(name: str, val: str) -> None:
    with open(f"secrets/{name}", "w", encoding="utf-8") as secret:
        secret.write(val)
