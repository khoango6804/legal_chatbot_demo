#!/usr/bin/env python3
import argparse
import json
import sys

import requests


def main():
    parser = argparse.ArgumentParser(description="Quick helper to query the local backend /chat endpoint.")
    parser.add_argument("question", nargs="+", help="Vietnamese question to send.")
    parser.add_argument("--url", default="http://127.0.0.1:8100/chat", help="Backend chat endpoint.")
    args = parser.parse_args()

    question = " ".join(args.question)
    payload = {"question": question}
    try:
        resp = requests.post(args.url, json=payload, timeout=30)
        print("Status:", resp.status_code)
        print(resp.text)
    except Exception as exc:
        print("Request failed:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

