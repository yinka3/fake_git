import itertools
import operator
import os
import string
from collections import namedtuple, deque

from . import data, diff
from .data import GIT_DIR, get_ref

Commit = namedtuple('Commit', ['tree', 'parents', 'message'])

def init():
    data.init()
    data.update_ref('HEAD', data.RefValue(symbolic=True, value='refs/heads/master'))

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
        assert '/' not in name
        assert name not in ('..', '.')
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
    if message == '#': message = 'No commit message'

    commit = f'tree {write_tree()}\n'

    HEAD = data.get_ref('HEAD').value
    if HEAD:
        commit += f'parent {HEAD}\n'
    MERGE_HEAD = data.get_ref('MERGE_HEAD').value
    if MERGE_HEAD:
        commit += f'parent {MERGE_HEAD}\n'
        data.delete_ref("MERGE_HEAD", deref=False)
    commit += "\n"
    commit += f'{message}\n'


    oid = data.hash_object(commit.encode(), 'commit')
    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))
    return oid

def get_commit(oid):
    parents = []

    commit = data.get_object(oid, 'commit').decode()
    lines = iter(commit.splitlines())

    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(' ', 1)
        if key == 'parent':
            parents.append(value)
        elif key == 'tree':
            tree = value
        else:
            assert False, f'Unknown field {key}'

    message = '\n'.join(lines)
    return Commit(tree=tree, parents=parents, message=message)

def checkout(name):
    oid = get_oid(name)
    commit = get_commit(oid)
    read_tree(commit.tree)

    if is_branch(name):
        HEAD = data.RefValue(symbolic=True, value=f'refs/heads/{name}')
    else:
        HEAD = data.RefValue(symbolic=False, value=oid)

    data.update_ref('HEAD', HEAD)

def is_branch(name):
    return data.get_ref(f'refs/heads/{name}').value is not None

def create_tag(name, oid):
    data.update_ref(f'refs/tags/{name}', data.RefValue(symbolic=False, value=oid))

def create_branch(name, oid):
    data.update_ref(f'refs/heads/{name}', data.RefValue(symbolic=False, value=oid))

def iter_commits_and_parents(oids):
    oids = deque(oids)
    visited = set()

    while oids:
        oid = oids.popleft()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid

        commit = get_commit(oid)
        oids.extendleft(commit.parents[:1])
        oids.extend(commit.parents[1:])


def get_oid(name):
    if name == '@': name = 'HEAD'

    refs_paths = [f'{name}', f'refs/{name}', f'refs/tags/{name}',f'refs/heads/{name}']

    for ref in refs_paths:
        if data.get_ref(ref, deref=False).value:
            return data.get_ref(ref).value

    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name

    assert False, f"Unknown name: {name}"

def get_branch_name():
    HEAD = data.get_ref('HEAD', deref=False)
    if not HEAD.symbolic:
        return None
    assert HEAD.value.startswith('refs/heads/')
    return os.path.relpath(HEAD.value, 'refs/heads/')

def iter_branch_names():
    for ref_name, _ in data.iter_refs('refs/heads/'):
        yield  os.path.relpath(ref_name, 'refs/heads/')

def reset(oid):
    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))

def get_working_tree():
    result = {}
    for root, _, files in os.walk('.'):
        for file in files:
            path = os.path.relpath(f"{root}/{file}")
            if is_ignored(path) or not os.path.isfile(path):
                continue
            with open(path, 'rb') as f:
                result[path] = data.hash_object(f.read())

    return result

def read_tree_merged(t_HEAD, t_other):
    _delete_cd()
    for path, blob in diff.merge_trees(get_tree(t_HEAD), get_tree(t_other)).items():
        os.makedirs(f'./{os.path.dirname(path)}', exist_ok=True)
        with open(path, 'wb') as f:
            f.write(blob)


def merge(other_branch):
    HEAD = data.get_ref('HEAD').value
    assert HEAD
    c_HEAD = get_commit(HEAD)
    c_other = get_commit(other_branch)

    data.update_ref('MERGE_HEAD', data.RefValue(symbolic=False, value=other_branch))
    read_tree_merged(c_HEAD, c_other)
    print("Just merged in working directory\nPlease commit")

def get_merge_base(oid1, oid2):
    parent1 = set(iter_commits_and_parents({oid1}))

    for oid in iter_commits_and_parents({oid2}):
        if oid in parent1:
            return oid


def is_ignored (path):
    return '.fake-git' in path.split('/')