import os
import hashlib
from collections import namedtuple

GIT_DIR = ".fake-git"
# object database

RefValue = namedtuple('RefValue', ['symbolic', 'value'])

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

def iter_refs():
    refs = ["HEAD"]
    for root, _, files in os.walk(f'{GIT_DIR}/refs/'):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f'{root}/{name}' for name in files)

    for ref_name in refs:
        yield ref_name, get_ref(ref_name)

def update_ref(ref, value):
    assert not value.symbolic
    ref_path = f'{GIT_DIR}/{ref}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open (ref_path, "w") as f:
        f.write(value.value)

def get_ref(ref):
    ref_path = f'{GIT_DIR}/{ref}'
    value = None
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            value = f.read().strip()

    if value and value.startswith('ref:'):
        return get_ref(value.split(':', 1)[1].strip())

    return RefValue(symbolic=False, value=value)


