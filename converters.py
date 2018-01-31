import hashlib


def id_2_addr(address):
    m = hashlib.md5()
    m.update(address.encode())
    return m.hexdigest()[-14:]