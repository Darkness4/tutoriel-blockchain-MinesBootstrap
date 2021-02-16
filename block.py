import json
import time
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Iterable, List, Optional

from transaction import Transaction


@dataclass
class Block:
    index: int
    previous_hash: str
    nonce: int = 0
    timestamp: float = time.time()
    miner: Optional[str] = None
    hashval: Optional[str] = None
    __transactions: List[Transaction] = field(default_factory=list)

    @property
    def transactions(self) -> List[Transaction]:
        return self.__transactions

    def add_transactions(self, transactions: Iterable[Transaction]):
        for transaction in transactions:
            self.add_transaction(transaction)

    def add_transaction(self, transaction: Transaction):
        transaction.tx_number = len(self.transactions)
        self.__transactions.append(transaction)

    def compute_hash(self) -> str:
        data = json.dumps(asdict(self), sort_keys=True)
        return sha256(data.encode("utf-8")).hexdigest()

    def mine(self, difficulty: int) -> str:
        computed_hash = self.compute_hash()

        while not computed_hash.startswith("0" * difficulty):
            self.nonce += 1
            computed_hash = self.compute_hash()

        self.hashval = computed_hash

        return computed_hash

    def verify_hash(self) -> bool:
        return self.compute_hash() == self.hashval
