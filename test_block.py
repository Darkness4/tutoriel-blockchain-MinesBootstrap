import time

from block import Block
from key import BitcoinAccount
from transaction import Transaction

wallet = BitcoinAccount()

difficulty: int = 4

first_block = Block(0, "")

tx = Transaction("mohamed", "justine", 50, time.time())

first_block.add_transaction(tx)
first_block.mine(difficulty)

print("First block is: ")

print(first_block)

last_hash = first_block.hashval

if last_hash == None:
    raise ValueError("hash is None.")

second_block = Block(1, last_hash)

second_block.mine(difficulty)

print("Second block is: ")

print(second_block)
