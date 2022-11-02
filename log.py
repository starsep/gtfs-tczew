from rich.console import Console

console = Console(stderr=True)


def printInfo(message: str):
    console.print(message, style="blue")


def printWarning(message: str):
    console.print(message, style="yellow")


def printError(message: str):
    console.print(message, style="red")
