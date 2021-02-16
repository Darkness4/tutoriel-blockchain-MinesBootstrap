import json
import logging
import time
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional

from transaction import Transaction


@dataclass
class Block:
    index: int
    previous_hash: str
    nonce: int = 0
    timestamp: float = time.time()
    miner: Optional[str] = None
    hashval: Optional[str] = None
    transactions: List[Transaction] = field(default_factory=list)

    def add_transactions(self, transactions: Iterable[Transaction]):
        for transaction in transactions:
            self.add_transaction(transaction)

    def add_transaction(self, transaction: Transaction):
        transaction.tx_number = len(self.transactions)
        self.transactions.append(transaction)

    def compute_hash(self) -> str:
        data_dict = asdict(self)
        del data_dict["hashval"]
        data = json.dumps(data_dict, sort_keys=True)
        return sha256(data.encode("utf-8")).hexdigest()

    def mine(self, difficulty: int) -> str:
        computed_hash = self.compute_hash()

        while not computed_hash.startswith("0" * difficulty):
            self.nonce += 1
            computed_hash = self.compute_hash()

        self.hashval = computed_hash

        return computed_hash

    def hash_is_valid(self, difficulty) -> bool:
        if self.compute_hash() != self.hashval:
            logging.error(
                f"self.compute_hash()={self.compute_hash()} != self.hashval={self.hashval}"
            )
            return False

        if not self.hashval.startswith("0" * difficulty):
            logging.error(f"hashval doesn't start with {difficulty} zero")
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            index=int(data["index"]),
            previous_hash=data["previous_hash"],
            nonce=int(data["nonce"]),
            timestamp=float(data["timestamp"]),
            miner=data["miner"],
            hashval=data["hashval"],
            transactions=list(
                map(Transaction.from_dict, data["transactions"])
            ),
        )

    @classmethod
    def from_json(cls, data: str):
        data_dict = json.loads(data)
        return cls.from_dict(data_dict)
