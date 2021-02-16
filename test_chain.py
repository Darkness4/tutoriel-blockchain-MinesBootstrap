import json

from chain import Blockchain
from key import BitcoinAccount

wallet = BitcoinAccount()
address = wallet.to_address()
difficulty = 4

blockchain = Blockchain(difficulty)
blockchain.create_genesis_block()

print("blockchain: ")
print(blockchain.to_dict())

first_block = blockchain.head

print("First block: ")
print(first_block)

blockchain.add_transaction(address, "colas", 10)
blockchain.add_transaction(address, "salim", 30)
blockchain.mine_block()

print("blockchain: ")
print(json.dumps(blockchain.to_dict(), indent=2))
second_block = blockchain.head

print("Second block: ")
print(second_block)

print(f"Validity: {blockchain.is_valid()}")

blockchain.to_jsonfile()
blockchain2 = Blockchain.from_jsonfile()
print(f"Equality: {blockchain == blockchain2}")