from dataclasses import asdict, dataclass
import json
from typing import Any, Dict, Optional
import hashlib


@dataclass
class Transaction:
    sender: str
    receiver: str
    amount: float
    timestamp: float = 0
    tx_number: Optional[int] = None

    def __hash__(self):
        data = (
            self.sender
            + self.receiver
            + str(self.amount)
            + str(self.timestamp)
        )
        return int.from_bytes(
            hashlib.sha256(data.encode("utf-8")).digest(), "big"
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            sender=data["sender"],
            receiver=data["receiver"],
            amount=float(data["amount"]),
            timestamp=float(data["timestamp"]),
            tx_number=None
            if data["tx_number"] is None
            else int(data["tx_number"]),
        )

    @classmethod
    def from_json(cls, data: str):
        data_dict = json.loads(data)
        return cls.from_dict(data_dict)
