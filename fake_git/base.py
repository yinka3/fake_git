import os
from . import data

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
                    oid = data.hash_object(_f.read()), full
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

def is_ignored (path):
    return '.fake-git' in path.split('/')