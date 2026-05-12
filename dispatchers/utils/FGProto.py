# ============================================
# Author: Pavel P.
# Project: Fastgram
# Year: 2025
#
# This file was created by the author listed above.
# All rights reserved.
# Unauthorized copying, distribution, or modification is prohibited.
# ============================================

import json
import logging
import os
import random
import struct
import base64
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import asyncio
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


class FGProto:
    def __init__(self, type, client):
        self.type = type
        self.client = client

    class Error(Exception):
        def __init__(self, proto, message:str, enc_key:bytes, error_code:str|None = None, client=None, type="null"):
            self.message = message
            super().__init__(self.message)
            loop = asyncio.get_event_loop()
            loop.create_task(proto.send_message({"is_ok": False, "type": type, "error": message, "err_code": f"#{error_code}"}, enc_key, client_usr=client))

    async def generate_ecdh_keypair(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return {
            "private_key": private_key,
            "public_key": public_key,
            "public_key_pem": public_key_bytes
        }

    async def encrypt(self, data: bytes, key: bytes) -> bytes:
        nonce = os.urandom(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return nonce + tag + ciphertext

    async def decrypt(self, encrypted_data: bytes, key: bytes) -> bytes:
        if len(encrypted_data) < 28:
            raise ValueError("Повреждённые или слишком короткие зашифрованные данные")

        nonce = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]

        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)

    async def handshake(self):
        type = self.type
        client = self.client
        from websocket import ENCRYPTION_KEYS

        if not client:
            return {
                'is_ok': False,
                'error': 'No client provided. Please provide a client to handshake.'
            }

        if type == 'ws':
            ecdh_server_keys = await self.generate_ecdh_keypair()
            ENCRYPTION_KEYS[client]['ECDH']['server'] = {
                'private_key': ecdh_server_keys['private_key'],
                'public_key': ecdh_server_keys['public_key'],
                'public_key_pem': ecdh_server_keys['public_key_pem']
            }
            await client.send_bytes(ENCRYPTION_KEYS[client]['ECDH']['server']['public_key_pem'])
            shared_key = ENCRYPTION_KEYS[client]['ECDH']['server']['private_key'].exchange(ec.ECDH(),
                                                                                           ENCRYPTION_KEYS[client][
                                                                                               'ECDH'][
                                                                                               'client_public_key'])
            return {
                'is_ok': True,
                'key': shared_key,
            }
        else:
            return {
                'is_ok': False,
                'error': 'Unknown connection type provided.'
            }

    async def send_message(self, message:dict, enc_key:bytes, client_usr=None) -> bool:
        type = self.type
        client = self.client
        if client_usr:
            client = client_usr
        if type == 'ws':
            msg = await self.encrypt(json.dumps(message).encode('utf-8'), enc_key)
            print(f"SEND MESSAGE: {message}")
            await client.send_bytes(msg)
            return True
        else:
            return False
