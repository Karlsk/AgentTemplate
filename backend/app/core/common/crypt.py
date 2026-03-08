
# 给予base64的加密和解密功能
import base64


def base64_encrypt(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')


def base64_decrypt(text):
    return base64.b64decode(text.encode('utf-8')).decode('utf-8')
