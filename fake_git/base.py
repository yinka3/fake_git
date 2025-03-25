import itertools
import operator
import os
from collections import namedtuple

from . import data

Commit = namedtuple('Commit', ['tree', 'parent', 'message'])

def write_tree(directory='.'):
    entries = []
    with os.scandir(directory) as f:
        for entry in f:
            full = f"{directory}/{entry.name}"

            if is_ignored(full):
                continue
            if entry.is_file(follow_symlinks=False):
                _type = 'blob'
                with open (full, 'rb') as _f:
                    oid = data.hash_object(_f.read())
            elif entry.is_dir(follow_symlinks=False):
                _type = 'tree'
                oid = write_tree(full)
            entries.append((entry.name, oid, _type))

    tree = "".join(
        f"{_type} {oid} {name}\n"
        for name, oid, _type in sorted(entries)
    )
    return data.hash_object(tree.encode(), 'tree')

def _iter_tree_entries(oid):

    if not oid:
        return

    tree = data.get_object(oid, 'tree')
    for entries in tree.decode().splitlines():
        _type, oid, name = entries.split(" ", 2)
        yield _type, oid, name

def get_tree(oid, base_path=''):
    result = {}

    for _type, oid, name in _iter_tree_entries(oid):
        path = base_path + name
        if _type == 'blob':
            result[path] = oid
        elif _type == 'tree':
            result.update(get_tree(oid, f'{path}/'))
        else:
            raise AssertionError(f'Unknown entry type: {_type}')
    return result

def _delete_cd():
    for root, dirs, files, in os.walk(".", topdown=False):
        for file in files:
            path = os.path.relpath(f'{root}/{file}')
            if is_ignored(path) or not os.path.isfile(path):
                continue
        for dir in dirs:
            path = os.path.relpath(f'{root}/{dir}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                pass


def read_tree(tree_oid):
    _delete_cd()
    for path, oid in get_tree(tree_oid, base_path='./').items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object(oid))


def commit(message):
    commit = f'tree {write_tree()}\n'

    HEAD = data.get_ref('HEAD')
    if HEAD:
        commit += f'parent {HEAD}\n'
    commit += "\n"
    commit += f'{message}\n'

    oid = data.hash_object(commit.encode(), 'commit')
    data.update_ref('HEAD', oid)
    return oid

def get_commit(oid):
    parent = None

    commit = data.get_object(oid, 'commit').decode()
    lines = iter(commit.splitlines())

    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(' ', 1)
        if key == 'parent':
            parent = value
        elif key == 'tree':
            tree = value
        else:
            assert False, f'Unknown field {key}'

    message = '\n'.join(lines)
    return Commit(tree=tree, parent=parent, message=message)

def checkout(oid):
    commit = get_commit(oid)
    read_tree(commit.tree)
    data.update_ref('HEAD', oid)

def create_tag(name, oid):
    data.update_ref(f'ref/tags/{name}', oid)

def get_oid(name):
    return data.get_ref(name) or name

def is_ignored (path):
    return '.fake-git' in path.split('/')