import contextlib
import os
import hashlib
from collections import namedtuple

GIT_DIR = None
# object database

RefValue = namedtuple('RefValue', ['symbolic', 'value'])

@contextlib.contextmanager
def change_git_dir(new_dir):
    global GIT_DIR
    old_dir = GIT_DIR
    GIT_DIR = f'{new_dir}/.fake-git'
    yield
    GIT_DIR = old_dir

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

def iter_refs(prefix='', deref=True):
    refs = ['HEAD', 'MERGE_HEAD']

    for root, _, files in os.walk(f'{GIT_DIR}/refs/'):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f'{root}/{name}' for name in files)

    for ref_name in refs:
        if not ref_name.startswith(prefix):
            continue
        ref = get_ref(ref_name, deref=deref)
        if ref_name.value:
            yield ref_name, ref

def update_ref(ref, value, deref=True):
    ref = _get_ref_internal(ref, deref)[0]
    assert value.value

    if value.symbolic:
        value = f'ref: {value.value}'
    else:
        value = value.value

    ref_path = f'{GIT_DIR}/{ref}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open (ref_path, "w") as f:
        f.write(value)


def get_ref(ref, deref=True):
    return _get_ref_internal(ref, deref)[1]

def delete_ref(ref, deref=True):
    ref = _get_ref_internal(ref, deref)[0]
    os.remove(f'{GIT_DIR}/{ref}')

def _get_ref_internal(ref, deref):
    ref_path = f'{GIT_DIR}/{ref}'
    value = None
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            value = f.read().strip()

    is_symbolic = bool(value) and value.startswith('ref:')
    if is_symbolic:
        value = value.split(':', 1)[1].strip()

        if deref:
            return _get_ref_internal(value, deref=True)

    return ref, RefValue(symbolic=is_symbolic, value=value)


