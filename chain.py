import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

from block import Block
from transaction import Transaction


@dataclass
class Blockchain:
    difficulty: int
    __unconfirmed_transactions: List[Transaction] = field(default_factory=list)
    __chain: List[Block] = field(default_factory=list)

    def __post_init__(self):
        self.create_genesis_block()

    def create_genesis_block(self):
        if self.__chain:
            logging.warning(
                "Blockchain is not empty. No genesis block created."
            )
            return
        block = Block(index=0, previous_hash="0", timestamp=time.time())
        block.mine(self.difficulty)
        self.__chain.append(block)

    @property
    def chain(self) -> Tuple[Block]:
        return tuple(self.__chain)

    @property
    def head(self) -> Block:
        return self.__chain[-1]

    def to_dict(self) -> Dict[str, Any]:
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
        self.__unconfirmed_transactions.append(transaction)

    def mine_block(self) -> int:
        if not self.__unconfirmed_transactions:
            return -1

        if self.head.hashval == None:
            raise Exception("hashval of blockchain head is None.")

        new_block = Block(
            index=self.head.index + 1,
            timestamp=time.time(),
            previous_hash=self.head.hashval,
        )
        new_block.add_transactions(self.__unconfirmed_transactions)
        new_block.mine(self.difficulty)
        self.__chain.append(new_block)
        self.__unconfirmed_transactions = []
        return new_block.index
