import json
import time
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Iterator, List, overload

from key import verify_signature
from transaction import Transaction


@dataclass
class Block:
    index: str
    previous_hash: str
    nonce: int = 0
    timestamp: float = 0.0
    hashval: str = None
    miner: str = None
    __transactions: List[Transaction] = field(default_factory=list)

    @property
    def transactions(self) -> List[Transaction]:
        return self.__transactions

    def add_transactions(self, transactions: Iterator[Transaction]):
        for transaction in transactions:
            self.add_transaction(transaction)

    def add_transaction(self, transaction: Transaction):
        transaction.tx_number = len(self.transactions)
        self.__transactions.append(transaction)

    def compute_hash(self) -> str:
        data = json.dumps(asdict(self), sort_keys=True)
        return sha256(data.encode("utf-8")).hexdigest()

    def mine(self, difficulty: int):
        computed_hash = self.compute_hash()

        while not computed_hash.startswith("0" * difficulty):
            self.nonce += 1
            computed_hash = self.compute_hash()

        return computed_hash

    def verify_hash(self):
        return self.compute_hash() == self.hashval
