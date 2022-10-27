import sys


def printWarning(message: str):
    print(f"\033[93m{message}\033[0m", file=sys.stderr)
