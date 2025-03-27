import argparse
import sys
import textwrap
import subprocess
from time import sleep
import os
from . import data, base, diff

def main():
    args = parse_arg()
    args.func(args)

def parse_arg():
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest='command')
    commands.required = True

    oid = base.get_oid

    init_parser = commands.add_parser('init')
    init_parser.set_defaults(func=init)

    hash_obj_parser = commands.add_parser('hash-object')
    hash_obj_parser.set_defaults(func=hash_object)
    hash_obj_parser.add_argument('file')

    cat_file_parser = commands.add_parser('cat-file')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument('object', type=oid)

    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=write_tree)

    read_tree_parser = commands.add_parser('read-tree')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree', type=oid)

    commit_parser = commands.add_parser('commit')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('-m','--message', default="#", nargs='?')


    log_parser = commands.add_parser('log')
    log_parser.set_defaults(func=log)
    log_parser.add_argument('oid', default="@", type=oid,  nargs='?')

    checkout_parser = commands.add_parser('checkout')
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument('commit')

    tag_parser = commands.add_parser('tag')
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument('oid', default="@", type=oid, nargs='?')

    k_parser = commands.add_parser('k')
    k_parser.set_defaults(func=k)

    branch_parser = commands.add_parser('branch')
    branch_parser.set_defaults(func=branch)
    branch_parser.add_argument('name', nargs='?')
    branch_parser.add_argument('start_point', default='@', type=oid, nargs='?')

    status_parser = commands.add_parser('status')
    status_parser.set_defaults(func=status)

    reset_parser = commands.add_parser('reset')
    reset_parser.set_defaults(func=reset)
    reset_parser.add_argument('commit', type=oid)

    show_parser = commands.add_parser('show')
    show_parser.set_defaults(func=show)
    show_parser.add_argument('oid', type=oid, nargs='?')

    diff_parser = commands.add_parser('diff')
    diff_parser.set_defaults(func=_diff)
    diff_parser.add_argument('commit', default='@', type=oid, nargs='?')

    return parser.parse_args()

def init(args):
    print('Initializing...')
    base.init()
    sleep(2)
    print(f"Initialized empty fake-git repo in {os.getcwd()}/{data.GIT_DIR}")


def hash_object(args):
    with open (args.file, "rb") as f:
        print(data.hash_object(f.read()))

def cat_file(args):
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(args.object, expected=None))

def write_tree(args):
    print('Writing to tree...')
    print(base.write_tree())
    sleep(1)
    print('Done!')

def read_tree(args):
    print('Reading from tree...')
    base.read_tree(args.tree)
    sleep(1)
    print('Done!')

def commit(args):
    print('Commiting...')
    print(base.commit(args.message))
    sleep(1)
    print('Done!')

def log(args):
    refs = {}

    for ref_name, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(ref_name)

    for oid in base.iter_commits_and_parents({args.oid}):
        commit = base.get_commit(oid)
        _print_commit(oid, commit, refs.get(oid))

def checkout(args):
    base.checkout(args.commit)

def tag(args):
    base.create_tag(args.name, args.oid)

def k(args):
    dot = 'digraph commits{\n'
    oids = set()

    for ref_name, ref_oid in data.iter_refs(deref=False):
        dot += f'"{ref_name}" [shape=note]\n'
        dot += f'"{ref_name}" -> "{ref_oid.value}"\n'

        if not ref_oid.symbolic:
            oids.add(ref_oid.value)

    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [shape=box style=filled label="{oid[:10]}"]\n'
        if commit.parent:
            dot += f'"{oid}" -> "{commit.parent}"\n'

    dot += '}'
    print(dot)

    with subprocess.Popen (
        ['dot', '-Tx11', '/dev/stdin'],
        stdin=subprocess.PIPE) as proc:
        proc.communicate (dot.encode ())

def branch(args):

    if not args.name:
        current = base.get_branch_name()
        for branch in base.iter_branch_names():
            prefix = "*" if branch == current else ' '
            print(f'{prefix} {branch}')
    else:
        base.create_branch(args.name, args.start_point)
        print(f'Branch {args.name} created at {args.start_point[:10]}')


def status(args):
    HEAD = base.get_oid("@")
    branch = base.get_branch_name()
    if branch:
        print(f"On branch {branch}")
    else:
        print(f'HEAD detached at {HEAD[:10]}')

    print('\nChanges to be committed:\n')
    HEAD_tree = HEAD and base.get_commit(HEAD).tree
    for path, action in diff.iter_changed_files(base.get_tree(HEAD_tree), base.get_working_tree()):
        print(f'{action:>12} {path}')

def reset(args):
    base.reset(args.commit)

def _print_commit(oid, commit, refs=None):
    refs_str = f'({", ".join(refs)})' if refs else ""
    print(f'Commit: {oid} {refs_str}\n')
    print(textwrap.indent(commit.message, '  '))
    print('')

def show(args):
    if not args.oid:
        return
    commit = base.get_commit(args.oid)
    par_tree = None
    if commit.parent:
        par_tree = base.get_commit(commit.parent).tree
    _print_commit(args.oid, commit)
    result = diff.diff_trees(base.get_tree (par_tree), base.get_tree(commit.tree))
    sys.stdout.flush()
    sys.stdout.buffer.write(result)

def _diff(args):
    tree = args.commit and base.get_commit(args.commit).tree

    result = diff.diff_trees(base.get_tree (tree), base.get_working_tree())
    sys.stdout.flush()
    sys.stdout.buffer.write(result)
