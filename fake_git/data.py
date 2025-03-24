import os
import hashlib

GIT_DIR = ".fake-git"
# object database

def init():
    os.makedirs(os.path.join(GIT_DIR, "objects"))

#TODO: Try to add compression to it
def hash_object(data, _type="blob"):
    obj = _type.encode() + b'\x00' + data
    oid = hashlib.sha1(data).hexdigest()
    with open (os.path.join(GIT_DIR, "objects", oid) , "wb") as f:
        f.write(obj)
    return oid

def get_object(oid, expected='blob'):
    with open (os.path.join(GIT_DIR, "objects", oid) , "rb") as f:
        obj = f.read()

    _type, _, content = obj.partition(b'\x00')
    _type = _type.decode()

    if expected is not None:
        assert _type == expected, f'Expected {expected}, got {_type}'
    if expected is not None and _type != expected:
        raise ValueError(f'Expected {expected}, got {_type}')
    return content


