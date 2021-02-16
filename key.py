import hashlib  # for Bitcoin hashing
import json
from os import urandom
from typing import Optional, Union  # Should be a good source of entropy

import coincurve
from base58 import b58decode, b58encode  # for Bitcoin encoding
from coincurve.keys import (
    PublicKey,
)  # faster than ecdsa to compute public key from private key

max_32bitvalue = 0xFFFFFFFF
bitcoin_wifprefix = 0x80
bitcoin_addrprefix = 0x00


def curveorder():
    maxval = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    return maxval


def gen_private_key():
    # max value of the eliptic curve

    maxval = curveorder()
    p = urandom(32)  # almost any 32 random bytes array is a private key
    pint = int.from_bytes(p, "big")

    while pint > maxval or pint < 0:  # a private key cannot be zero (or below)
        # and should be lower than the maximal value of the eliptic curve
        p = urandom(32)
        pint = int.from_bytes(p, "big")
    return p


def priv_to_pub(key: bytes, compressed: bool = True):
    pub: PublicKey = coincurve.PublicKey.from_secret(key)
    return pub.format(compressed=compressed)


def priv_to_pub_raw(key: bytes):  # only for ecdsa-secp256k1 curve
    return priv_to_pub(key, compressed=False)[1:]


def pub_to_pub(pub: bytes, compressed: bool = True):
    return coincurve.PublicKey(pub).format(compressed=compressed)


class Account:
    def __init__(self, private: Optional[bytes] = None):
        if private is None:  # need to check type of input (bytes only)
            private = gen_private_key()
        self.pk = private
        self.curve = "ecdsa-secp256k1"

    @classmethod
    def fromhex(cls, hexa: str):  # need to check type of input (str only)
        return cls(bytes.fromhex(hexa))

    @classmethod
    def fromfile(cls, file_name: str):
        with open(file_name) as json_file:
            data = json.load(json_file)
            return cls.fromhex(data["private_key"])

    def private_key(self):
        return self.pk.hex()

    def to_file(self, file_name: str):
        key = {"private_key": self.private_key()}
        with open(file_name, "w") as key_file:
            json.dump(key, key_file)

    def sign(self, message: str) -> bytes:
        pk = coincurve.PrivateKey(self.pk)
        signature = pk.sign_recoverable(message.encode())
        return signature


def hash256(x: bytes):
    return hashlib.sha256(x).digest()


def doublehash(x: bytes):
    return hash256(hash256(x))


def ripemd160(x: bytes):
    return hashlib.new("ripemd160", data=x).digest()


def hash160(x: bytes):
    return ripemd160(hash256(x))


def wif_to_priv(wif: Union[str, bytes], compressed: bool = True) -> bytes:
    pkeychecked = b58decode(wif)  # convert to base58

    # remove firt byte (network flag)
    # and last 4 bytes (checksum)
    # or last 5 bytes for compressed because of the compressed byte flag
    return pkeychecked[1:-5] if compressed else pkeychecked[1:-4]


def public_to_P2PKH(
    public_key: bytes,
    compressed: bool = True,
    network_addrprefix: int = bitcoin_wifprefix,
):
    public = pub_to_pub(public_key, compressed=True)
    encrypted_pub = bytes([network_addrprefix]) + hash160(public)
    check = doublehash(encrypted_pub)
    checksum = check[:4]
    address = encrypted_pub + checksum
    return b58encode(address).decode()


class BitcoinAccount(Account):
    network_wifprefix = bitcoin_wifprefix
    network_addrprefix = bitcoin_addrprefix

    def __init__(self, private: Optional[bytes] = None):
        super().__init__(private)

    @classmethod
    def fromwif(cls, wif: Union[str, bytes]):
        return cls(wif_to_priv(wif))

    def to_file(self, file_name: Optional[str] = None):
        if file_name == None:
            file_name = self.to_address() + ".json"
        super().to_file(file_name)  #  check parameter less

    def to_wif(self, compressed: bool = True):
        s1 = bytes([self.network_wifprefix]) + self.pk
        if compressed:
            s1 += bytes([0x01])  # add compressed flag byte
        checksum = doublehash(s1)[:4]  # first 4 bytes = checksum
        wif = s1 + checksum
        return b58encode(wif).decode()

    def to_pub(self, compressed: bool = True):
        public = priv_to_pub(self.pk, compressed)
        return public

    def to_P2PKH(self, compressed: bool = True):
        pub = self.to_pub(compressed=compressed)
        return public_to_P2PKH(
            pub, compressed=True, network_addrprefix=self.network_wifprefix
        )

    def to_address(self, compressed: bool = True):
        return self.to_P2PKH(compressed=compressed)

    def __repr__(self, compressed: bool = True):
        string_val = (
            "WIF: "
            + str(self.to_wif(compressed))
            + "\n"
            + "Address: "
            + self.to_address(compressed)
        )
        return string_val


def verify_signature(signature: str, message: str, address: str):
    public_key: PublicKey = coincurve.PublicKey.from_signature_and_message(
        bytes.fromhex(signature), message.encode()
    )
    public_key_formatted = public_key.format()
    address_computed = public_to_P2PKH(public_key_formatted)
    return address_computed == address
