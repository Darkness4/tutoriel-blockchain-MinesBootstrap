import base64
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional

from key import Account, verify_signature
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
    signature: Optional[str] = None

    def add_transactions(self, transactions: Iterable[Transaction]):
        for transaction in transactions:
            self.add_transaction(transaction)

    def add_transaction(self, transaction: Transaction):
        transaction.tx_number = len(self.transactions)
        self.transactions.append(transaction)

    def compute_hash(self) -> str:
        data = (
            str(self.index)
            + str(self.previous_hash)
            + str(self.nonce)
            + str(self.timestamp)
            + str(self.miner)
        )
        for transaction in self.transactions:
            data += (
                str(transaction.sender)
                + str(transaction.receiver)
                + str(transaction.amount)
            )
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
            signature=data["signature"],
        )

    def sign(self, wallet: Account):
        data = self.to_dict()
        del data["signature"]
        message = json.dumps(data, sort_keys=True)
        signature = wallet.sign(message)
        self.signature = base64.b64encode(signature).decode("ascii")
        return signature

    def verify(self):
        data = self.to_dict()
        del data["signature"]
        message = json.dumps(data, sort_keys=True)

        if self.signature is None:
            logging.warning("Signature is None.")
            return False
        signature = base64.b64decode(self.signature.encode("ascii"))

        address = self.miner

        if (
            address is not None
            and verify_signature(signature.hex(), message, address) != True
        ):
            logging.warning(
                f"Signature Verification failed : signature={signature.hex()}"
            )
            return False

        # check every transaction
        for transaction in self.transactions:
            if (
                transaction.sender != "NETWORK_ADMIN"
                and transaction.verify() != True
            ):
                logging.warning(
                    f"Transaction Verification failed : {transaction}"
                )
                return False

        # check hash
        computed_hash = self.compute_hash()
        if computed_hash != self.hashval:
            logging.warning(
                f"Hash computed failed : computed_hash={computed_hash}, hashval={self.hashval}"
            )
            return False

        return True
