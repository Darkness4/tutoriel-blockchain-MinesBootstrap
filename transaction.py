from dataclasses import dataclass
from typing import Optional


@dataclass
class Transaction:
    sender: str
    receiver: str
    amount: float
    timestamp: float = 0
    tx_number: Optional[int] = None
