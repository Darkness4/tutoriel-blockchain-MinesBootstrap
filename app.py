import atexit
import json
import logging
import os
import sys
import threading
import time
import traceback
from functools import partial
from typing import Optional

import zmq
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import QObject, Qt, Signal, Slot
from zmq.sugar.socket import Socket

from block import Block
from chain import Blockchain
from key import BitcoinAccount
from transaction import Transaction

logger = logging.getLogger()

# wallet generation
wallet = BitcoinAccount()
address = wallet.to_address()
file_name = "wallets/" + address + ".json"
wallet.to_file(file_name)

#  blockchain data

difficulty = 3
blockchain: Optional[Blockchain] = None
peers = set()

# list_ports = ["5556", "5557", "5558"]

port_bind = "5000"
if len(sys.argv) > 1:
    port_bind = sys.argv[1]

context = zmq.Context()
socket: Socket = context.socket(zmq.PUB)

socket.bind("tcp://*:%s" % port_bind)

topic = ""
ip = "localhost" + ":" + port_bind
socket_sub: Socket = context.socket(zmq.SUB)
for elem in list(peers):
    if elem != ip:
        socket_sub.connect("tcp://%s" % elem)
socket_sub.setsockopt_string(zmq.SUBSCRIBE, topic)


class Connection(QObject):
    write_block = Signal(Block)
    write_transaction = Signal(Transaction)


ConnectionWrite = Connection()


def reading_network():
    global blockchain

    while True:
        try:
            data = socket_sub.recv_json()
            if "operation" in data:
                parameters = data["parameters"]
                if data["operation"] == "add_transaction":
                    add_transaction(parameters)
                elif data["operation"] == "add_peer":
                    add_peer(Blockchain.from_dict(parameters["blockchain"]))
                elif data["operation"] == "consensus":
                    if blockchain is not None:
                        socket.send_json(
                            {
                                "operation": "consensus_resp",
                                "parameters": {
                                    "blockchain": blockchain.to_dict()
                                },
                            }
                        )
                elif data["operation"] == "consensus_resp":
                    peer_blockchain = Blockchain.from_dict(
                        parameters["blockchain"]
                    )
                    if blockchain is None or (
                        len(peer_blockchain) > len(blockchain)
                        and peer_blockchain.is_valid()
                    ):
                        blockchain = peer_blockchain
                        socket.send_json(
                            {
                                "operation": "consensus_resp",
                                "parameters": {
                                    "blockchain": blockchain.to_dict()
                                },
                            }
                        )
                elif data["operation"] == "add_block":
                    add_block(parameters)

        except:
            traceback.print_exc()


def add_block(parameters):
    new_block = Block.from_dict(parameters["block"])
    if blockchain is None:
        socket.send_json(
            {
                "operation": "consensus",
                "parameters": None,
            }
        )
        return

    if new_block not in blockchain.blocks:
        if not new_block.verify():
            logging.warning("Block REJECTED: Basic verification failed.")
            logging.warning(f"Block was {new_block}.")
            return
        result = blockchain.add_block_from_peer(new_block)
        ConnectionWrite.write_block.emit(blockchain.head)

        if not result:
            logging.warning("A block from peer was discarded.")
        else:
            logging.warning(f"A block from peer was added: {result}")
            socket.send_json(
                {
                    "operation": "add_block",
                    "parameters": {"block": parameters["block"]},
                }
            )


def add_transaction(parameters):
    new_transaction = Transaction.from_dict(parameters["transaction"])
    if (
        new_transaction.sender != "NETTWORK_ADMIN"
        and not new_transaction.verify()
    ):
        logging.warning("Transaction REJECTED: Basic verification failed.")
        logging.warning(f"Transaction was {new_transaction}.")
        return
    if blockchain is not None and new_transaction.signature not in map(
        lambda x: x.signature, blockchain.tx_pool
    ):
        blockchain.add_transaction(transaction=new_transaction)
        socket.send_json(
            {
                "operation": "add_transaction",
                "parameters": {
                    "transaction": parameters["transaction"],
                },
            }
        )
        ConnectionWrite.write_transaction.emit(new_transaction)


def add_peer(new_blockchain: Blockchain):
    global blockchain

    if blockchain is None or len(new_blockchain) >= len(
        blockchain
    ):  # Pseudo-consensus
        validated_blockchain = Blockchain(difficulty)
        for block in new_blockchain.blocks:
            if block.index != 0:
                added = validated_blockchain.add_block_from_peer(block)
                if not added:
                    logging.error("Bad blockchain. No peer added.")
                    return
            else:
                validated_blockchain.blocks[0] = block

        if not validated_blockchain.is_valid():
            logging.error("Bad blockchain. No peer added.")
            return

        blockchain = validated_blockchain


class Chain_Dialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chain")

        chain_layout = QtWidgets.QFormLayout()

        chain_label = QtWidgets.QLabel(
            json.dumps(blockchain.to_dict(), indent=4, sort_keys=True)
        )
        chain_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)

        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea.setWidget(chain_label)
        self.scrollArea.setWidgetResizable(True)

        chain_layout.addWidget(self.scrollArea)
        self.setLayout(chain_layout)


class Tx_Dialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Send Transaction")

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttonBox.accepted.connect(self.working_click)
        self.buttonBox.rejected.connect(self.reject)

        tx_layout = QtWidgets.QFormLayout()

        self.tx_address = QtWidgets.QLineEdit()

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.tx_address.textChanged.connect(self.allowButton)

        self.tx_amount = QtWidgets.QSpinBox()
        self.tx_amount.setRange(0, 999999999)
        # self.tx_amount.setValue(0)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        tx_layout.addRow("Adress of receiver: ", self.tx_address)
        tx_layout.addRow("Amount to send: ", self.tx_amount)
        tx_layout.addWidget(self.buttonBox)
        self.setLayout(tx_layout)

    def allowButton(self):
        if len(self.tx_address.text()) > 0:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
                True
            )
        elif self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).isEnabled():
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
                False
            )

    def working_click(self):
        transaction = Transaction(
            address,
            self.tx_address.text(),
            float(self.tx_amount.text()),
            time.time(),
        )
        transaction.sign(wallet)
        blockchain.add_transaction(transaction)
        ConnectionWrite.write_transaction.emit(transaction)
        socket.send_json(
            {
                "operation": "add_transaction",
                "parameters": {
                    "transaction": transaction.to_dict(),
                },
            }
        )
        self.accept()


class Peer_Dialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add peer")

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttonBox.accepted.connect(self.working_click)
        self.buttonBox.rejected.connect(self.reject)

        tx_layout = QtWidgets.QFormLayout()

        self.peer_address = QtWidgets.QLineEdit()

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.peer_address.textChanged.connect(self.allowButton)

        self.setWindowModality(QtCore.Qt.ApplicationModal)
        tx_layout.addRow("Adress of receiver: ", self.peer_address)

        tx_layout.addWidget(self.buttonBox)
        self.setLayout(tx_layout)

    def allowButton(self):
        if len(self.peer_address.text()) > 0:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
                True
            )
        elif self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).isEnabled():
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(
                False
            )

    def get_peer(self):
        return self.peer_address.text()

    def working_click(self):
        # TODO: add send tx to other peers function here
        if blockchain != None:
            socket.send_json(
                {
                    "operation": "add_peer",
                    "parameters": {
                        "address": address,
                        "blockchain": blockchain.to_dict(),
                    },
                }
            )
        self.accept()


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        global ConnectionWrite

        self.text_address = QtWidgets.QLabel("My address: ")
        self.address_value = QtWidgets.QLabel(address)
        self.address_value.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.text_ip = QtWidgets.QLabel("My IP: ")
        self.ip_value = QtWidgets.QLabel(ip)
        self.ip_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.button_tx = QtWidgets.QPushButton("Send transaction")
        self.button_chain = QtWidgets.QPushButton("Chain")
        self.button_mine = QtWidgets.QPushButton("Mine")
        self.button_peer = QtWidgets.QPushButton("Add peer")

        self.text_peerlist = QtWidgets.QLabel("Peers: ")

        self.text_pending = QtWidgets.QLabel("Pending tx: ")

        self.text_block = QtWidgets.QLabel("Last block: ")

        self.layout = QtWidgets.QVBoxLayout()

        # layout for the address
        layout_address = QtWidgets.QHBoxLayout()
        layout_address.addWidget(self.text_address)
        layout_address.addWidget(self.address_value)
        self.layout.addLayout(layout_address)

        # layout for the ip
        layout_ip = QtWidgets.QHBoxLayout()
        layout_ip.addWidget(self.text_ip)
        layout_ip.addWidget(self.ip_value)
        self.layout.addLayout(layout_ip)

        # layout for the buttons

        layout_buttons = QtWidgets.QHBoxLayout()
        layout_buttons.addWidget(self.button_tx)
        layout_buttons.addWidget(self.button_chain)
        layout_buttons.addWidget(self.button_mine)
        layout_buttons.addWidget(self.button_peer)
        self.layout.addLayout(layout_buttons)

        self.layout.addWidget(self.text_peerlist)
        self.peers_layout = QtWidgets.QFormLayout()
        self.tx_layout = QtWidgets.QFormLayout()
        self.block_data = QtWidgets.QLabel()
        self.block_data.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )

        self.layout.addLayout(self.peers_layout)
        self.layout.addWidget(self.text_pending)
        self.layout.addLayout(self.tx_layout)
        self.layout.addWidget(self.text_block)
        self.layout.addWidget(self.block_data)

        self.setLayout(self.layout)

        self.button_tx.clicked.connect(self.send_tx)
        self.button_chain.clicked.connect(self.print_chain)
        self.button_mine.clicked.connect(self.mine_call)
        self.button_peer.clicked.connect(self.add_peer)

        ConnectionWrite.write_block.connect(self.define_block_from_thread)
        ConnectionWrite.write_transaction.connect(self.define_tx_from_thread)

    def print_chain(self):
        if blockchain:
            chain_window = Chain_Dialog()
            chain_window.exec_()

        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText(
                "No chain: you need to mine the first block or get the chain "
                "from another peer before seeing the chain"
            )
            msg.setWindowTitle("No blockchain")

            msg.exec_()

    def mine_call(self):
        global blockchain

        if blockchain is None:
            self.consensus()
            if blockchain is None:
                blockchain = Blockchain.create(difficulty, wallet)
        else:
            result = blockchain.mine_block(wallet)
            if not result:
                logging.info("No transaction to mine")
            else:
                chain_length = len(blockchain.blocks)
                self.consensus()
                if chain_length == len(blockchain.blocks):
                    socket.send_json(
                        {
                            "operation": "add_block",
                            "parameters": {
                                "block": blockchain.head.to_dict(),
                            },
                        }
                    )
        logging.info(f"HEAD: {blockchain.head}")
        self.define_block(blockchain.head)

    @staticmethod
    def consensus():
        socket.send_json(
            {
                "operation": "consensus",
                "parameters": None,
            }
        )
        time.sleep(2)

    @Slot(Block)
    def define_block_from_thread(self, block: Block):
        self.define_block(block)

    @Slot(Transaction)
    def define_tx_from_thread(self, transaction: Transaction):
        self.define_tx(transaction)

    def define_block(self, block):
        self.block_data.setText(
            json.dumps(block.to_dict(), sort_keys=True, indent=2)
        )
        for _ in range(self.tx_layout.rowCount()):
            self.tx_layout.removeRow(0)

    @staticmethod
    def send_tx():
        global blockchain
        # open the tx dialog window
        if blockchain:
            tx_window = Tx_Dialog()
            tx_window.exec_()
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText(
                "No chain: you need to mine the first block or get the chain "
                "from another peer before sending transactions"
            )
            msg.setWindowTitle("No blockchain")

            msg.exec_()

    def define_tx(self, transaction: Transaction):
        text = json.dumps(transaction.to_dict(), sort_keys=True, indent=2)
        text_tx = QtWidgets.QLabel(text)
        text_tx.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.tx_layout.addRow(text_tx)

    def define_peer(self, elem):
        text_peer = QtWidgets.QLabel(elem)
        text_peer.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        button_peer = QtWidgets.QPushButton("X")
        button_peer.setFixedSize(20, 20)
        button_peer.clicked.connect(
            partial(self.remove_peer, elem, text_peer, button_peer)
        )
        self.peers_layout.addRow(text_peer, button_peer)

    def add_peer(self):
        global ip
        peer_window = Peer_Dialog()
        ret_val = peer_window.exec_()
        if ret_val == 1:
            peer_address = peer_window.get_peer()
            if peer_address != ip:
                peers.add(peer_address)
                socket_sub.connect("tcp://%s" % peer_address)
                self.define_peer(peer_address)

    def remove_peer(self, elem, text_peer, button_peer):
        peers.remove(elem)
        socket_sub.disconnect("tcp://%s" % elem)

        button_peer.deleteLater()
        text_peer.deleteLater()


def clean_file():
    os.remove(file_name)


atexit.register(clean_file)

if __name__ == "__main__":
    t = threading.Thread(target=reading_network)
    t.daemon = True  #  to close when main loop close
    t.start()

    app = QtWidgets.QApplication([])

    widget = MyWidget()

    scrollArea = QtWidgets.QScrollArea()

    scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    scrollArea.setWidgetResizable(True)

    scrollArea.setWidget(widget)
    scrollArea.resize(800, 600)
    scrollArea.setWindowTitle("Blockchain")
    scrollArea.show()

    sys.exit(app.exec_())
