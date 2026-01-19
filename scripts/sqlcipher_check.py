#!/usr/bin/env python3
"""Verify SQLCipher driver availability and encryption support without starting the server."""
import os
import sys


def main() -> int:
    key = os.getenv("CUSTOS_DATABASE_KEY")
    if not key:
        print("CUSTOS_DATABASE_KEY is required for SQLCipher verification.")
        return 1

    try:
        import sqlcipher3
    except ImportError as exc:
        print("SQLCipher driver missing. Install sqlcipher3-binary.")
        print(f"Import error: {exc}")
        return 1

    try:
        conn = sqlcipher3.dbapi2.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key = '{key}';")
        cursor.execute("PRAGMA cipher_version;")
        cipher_version = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as exc:
        print(f"SQLCipher check failed: {exc}")
        return 1

    if not cipher_version or not cipher_version[0]:
        print("SQLCipher is not active. Encryption check failed.")
        return 1

    print(f"SQLCipher available: {cipher_version[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
