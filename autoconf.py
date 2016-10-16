"""
Automatically update your Dotbot config file when new files are committed in Git

The MIT License (MIT)
Copyright (c) 2016 Greg Werbin

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import yaml
from io import StringIO
from shutil import copy2 as cp
from pygit2 import Repository
from unidiff import PatchSet

def compose(g, f):
    gf = lambda *args: g(f(*args))
    return gf

tmap = compose(tuple, map)
expand_path = compose(os.path.abspath, os.path.expanduser)
star = lambda f: lambda *x: f(x)

def file_in_any(filename, directories):
    file_in = partial(os.path.commonprefix, star(os.path.commonprefix))
    return any(map(file_in, directories))

def get_added_files(repo, directories):
    """
    Get new files staged for commit
    """
    directories = tmap(os.path.abspath, directories)
    diff = repo.diff('HEAD', cached=True)
    patch = PatchSet(StringIO(diff.patch))
    return [f for f in patch.added_files if file_in_any(f, directories)]

def update_dotbot_conf(config_file, added_files):
    """
    Assumes you want to link all files into '~' and prepend a dot to the name
    e.g. for a new file "bashrc" it will generate:
        ~/.bashrc: bashrc
    """
    # create a backup, taking care to avoid a name conflict
    backup_file = config_file + '.bak'
    i = 0
    while os.access(backup_file, os.R_OK):
        backup_file += str(i)
        i += 1
    cp(config_file, backup_file)

    try:
        with open(config_file) as f:
            config = yaml.load(f)

        for link_from in added_files:
            link_to = os.path.join('~', '.' + os.path.split(link_from[1]))
            config['link'][link_to] = link_from

        with open(config_file) as f:
            yaml.dump(config, f)
    except Exception:
        cp(backup_file, config_file)
    finally:
        os.remove(backup_file)


def prepare_commit(repo, config_file):
    """
    Add the dotbot conf file to the staging area and add a comment in the commit
       message notifying the user that this was done
    """
    repo.index.add(config_file)
    # update commit message


def parse_args(defaults):
    """
    Parse CLI args, if any
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('directories', nargs='*', default=defaults['repo_root'], metavar='directory',
        help="Directories to restrict the update to (default: entire repository)")
    parser.add_argument('-c', '--config-file', nargs=1, metavar='file', dest='config_file',
        help="Alternate location of config file (default: '{}')".format(defaults['dotbot_conf']))

    parser.parse_args()
    config_file = parser.config_file[0]
    directories = parser.directories
    return config_file, directories


def make_defaults():
    """
    Return a dictionary of default values
    """
    defaults = {}

    defaults['repo_root'] = os.getenv('REPO_ROOT', '.')

    default_conf = os.path.join(defaults['repo_root'], 'dotbot.conf.yaml')
    defaults['dotbot_conf'] = os.getenv('DOTBOT_CONF', default_conf)

    return defaults


def main():
    defaults = make_defaults()
    config_file, directories = parse_args(defaults)

    repo = Repository(defaults['repo_root'])

    added_files = get_added_files(repo, directories, defaults['repo_root'])
    update_dotbot_conf(config_file, added_files)
    prepare_commit(repo, config_file)
