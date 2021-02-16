import json
import logging
import platform
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from block import Block
from transaction import Transaction


@dataclass
class Blockchain:
    difficulty: int
    blocks: List[Block] = field(default_factory=list)
    tx_pool: List[Transaction] = field(default_factory=list)
    block_reward: float = 50.0

    def __post_init__(self):
        self.create_genesis_block()

    def create_genesis_block(self):
        if self.blocks:
            logging.warning(
                "Blockchain is not empty. No genesis block created."
            )
            return
        block = Block(index=0, previous_hash="", timestamp=time.time())
        block.mine(self.difficulty)
        self.blocks.append(block)

    @property
    def head(self) -> Block:
        return self.blocks[-1]

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
        self.tx_pool.append(transaction)

    def mine_block(self) -> int:
        if not self.tx_pool:
            return -1

        if self.head.hashval == None:
            raise Exception("hashval of blockchain head is None.")

        new_block = Block(
            index=self.head.index + 1,
            timestamp=time.time(),
            previous_hash=self.head.hashval,
            miner=platform.node(),
        )
        new_block.add_transactions(self.tx_pool)
        new_block.mine(self.difficulty)
        self.__add_block(new_block)
        self.tx_pool.clear()
        return new_block.index

    def add_block_from_peer(self, new_block: Block):
        self.__add_block(new_block)

    def __add_block(self, new_block: Block):
        if new_block.timestamp < self.head.timestamp:
            logging.warning("Block REJECTED: Timestamp is not valid.")
            logging.warning(
                f"new_block.timestamp={new_block.timestamp} < head.timestamp={self.head.timestamp}"
            )
            return

        if new_block.index != self.head.index + 1:
            logging.warning("Block REJECTED: Index is not valid.")
            logging.warning(
                f"new_block.index={new_block.index} != head.index+1={self.head.index+1}"
            )
            return

        if new_block.previous_hash != self.head.hashval:
            logging.warning("Block REJECTED: Previous hash is not valid.")
            logging.warning(
                f"new_block.previous_hash={new_block.previous_hash} != head.hashval={self.head.hashval}"
            )
            return

        if not new_block.hash_is_valid(self.difficulty):
            logging.warning("Block REJECTED : Hash is not valid.")
            return

        self.blocks.append(new_block)

    def is_valid(self) -> bool:
        return all(
            map(lambda x: x.hash_is_valid(self.difficulty), self.blocks)
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_jsonfile(self, pathfile: str = "blockchain.json"):
        with open(pathfile, "w") as file:
            json.dump(self.to_dict(), file)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            difficulty=int(data["difficulty"]),
            blocks=list(map(Block.from_dict, data["blocks"])),
            tx_pool=list(map(Transaction.from_dict, data["tx_pool"])),
            block_reward=float(data["block_reward"]),
        )

    @classmethod
    def from_json(cls, data: str):
        data_dict = json.loads(data)
        return cls.from_dict(data_dict)

    @classmethod
    def from_jsonfile(cls, pathfile: str = "blockchain.json"):
        with open(pathfile, "r") as file:
            data_dict = json.load(file)
            return cls.from_dict(data_dict)
