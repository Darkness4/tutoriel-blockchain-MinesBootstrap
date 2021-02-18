import base64
import hashlib
import json
from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, Optional

from key import Account, verify_signature


@dataclass
class Transaction:
    sender: str
    receiver: str
    amount: float
    timestamp: float = 0
    tx_number: Optional[int] = None
    signature: Optional[str] = None

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
            signature=data["signature"],
        )

    def sign(self, wallet: Account):
        data = self.to_dict()
        del data["signature"]
        del data["tx_number"]
        message = json.dumps(data, sort_keys=True)
        signature = wallet.sign(message)
        self.signature = base64.b64encode(signature).decode("ascii")
        return signature

    def verify(self):
        data = self.to_dict()
        del data["signature"]
        del data["tx_number"]
        message = json.dumps(data, sort_keys=True)
        if self.signature is None:
            logging.warning("Signature is None.")
            return False
        signature = base64.b64decode(self.signature.encode("ascii"))
        address = self.sender
        return verify_signature(signature.hex(), message, address)
