from key import verify_signature
from dataclasses import dataclass


@dataclass
class Transaction:
    sender: str
    receiver: str
    amount: float
    timestamp: float = 0
    tx_number: int = None
