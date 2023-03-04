import uuid

SIDE_MAPPING = {
    "buy": "sell",
    "sell": "buy"
}


def flat_uuid() -> str:
    return str(uuid.uuid4()).replace('-', '')
