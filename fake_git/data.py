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

def update_ref(ref, oid):
    ref_path = f'{GIT_DIR}/{ref}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open (ref_path, "w") as f:
        f.write(oid)

def get_ref(ref):
    ref_path = f'{GIT_DIR}/{ref}'
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            return f.read().strip()