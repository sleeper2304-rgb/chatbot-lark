# ============================================
# Giải mã payload webhook Lark (Encrypt Key)
# Theo tài liệu: https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/encrypt-key-encryption-configuration-case
# ============================================

import hashlib
import base64
from Crypto.Cipher import AES


class AESCipher:
    def __init__(self, key: str):
        self.bs = AES.block_size
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data):
        u_type = type(b"".decode("utf8"))
        if isinstance(data, u_type):
            return data.encode("utf8")
        return data

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1 :])]

    def decrypt(self, enc: bytes) -> bytes:
        iv = enc[: AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size :]))

    def decrypt_string(self, enc_b64: str) -> str:
        enc = base64.b64decode(enc_b64)
        return self.decrypt(enc).decode("utf8")


def decrypt_lark_body(encrypt_b64: str, encrypt_key: str) -> str:
    if not encrypt_key:
        raise ValueError("encrypt_key rỗng")
    cipher = AESCipher(encrypt_key)
    return cipher.decrypt_string(encrypt_b64)
