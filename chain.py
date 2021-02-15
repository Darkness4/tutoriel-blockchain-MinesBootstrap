import copy
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import List

from block import Block
from transaction import Transaction


@dataclass
class Blockchain:
    difficulty: int
    unconfirmed_transactions: List[Transaction] = field(default_factory=list)
    chain: List[Block] = field(default_factory=list)

    def __post_init__(self):
        self.create_genesis_block()

    def create_genesis_block(self):
        if self.chain:
            logging.warning(
                "Blockchain is not empty. No genesis block created."
            )
            return
        block = Block(index=0, previous_hash="0", timestamp=time.time())
        block.hashval = block.compute_hash()
        self.chain.append(block)

    @property
    def head(self) -> Block:
        return self.chain[-1]

    def to_dict(self) -> dict:
        return asdict(self)

    def add_transaction(
        self,
        sender: str,
        receiver: str,
        amount: float,
    ):
        transaction = Transaction(
            sender=sender,
            receiver=receiver,
            amount=amount,
            timestamp=time.time(),
        )
        self.unconfirmed_transactions.append(transaction)

    def mine_block(self) -> int:
        if not self.unconfirmed_transactions:
            return -1

        new_block = Block(
            index=self.head.index + 1,
            timestamp=time.time(),
            previous_hash=self.head.hashval,
        )
        for transaction in self.unconfirmed_transactions:
            new_block.add_transaction(transaction)

        new_block.hashval = new_block.mine(self.difficulty)
        self.chain.append(new_block)
        self.unconfirmed_transactions = []
        return new_block.index
