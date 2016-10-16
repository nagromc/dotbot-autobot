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
import operator as op
from io import StringIO
from functools import partial
from itertools import chain

from shutil import copy2 as cp
from pygit2 import Repository
from unidiff import PatchSet

import logging
logger = logging.getLogger('dotbot-autoconf')
stream_handler = logging.StreamHandler()
if not logger.hasHandlers():
    logger.addHandler(stream_handler)

def compose(g, f):
    gf = lambda *args: g(f(*args))
    return gf

tmap = compose(tuple, map)
expand_path = compose(os.path.abspath, os.path.expanduser)
star = lambda f: lambda *x: f(x)
common_prefix = star(os.path.commonprefix)

def file_in_any(filename, directories):
    file_in = partial(common_prefix, filename)
    return any(map(file_in, directories))

def get_added_files(repo, directories):
    """
    Get new files staged for commit
    """
    directories = tmap(expand_path, directories)
    diff = repo.diff('HEAD', cached=True)
    patch = PatchSet(StringIO(diff.patch))
    logger.debug(str(diff.patch))
    logger.debug("Checking %s", directories)
    added_files = (f.path for f in patch.added_files)
    return [f for f in added_files if file_in_any(expand_path(f), directories)]

def update_dotbot_conf(config_file, added_files):
    """
    Assumes you want to link all files into '~' and prepend a dot to the name
    e.g. for a new file "bashrc" it will generate:
        ~/.bashrc: bashrc

    This should also be idempotent, in that it won't add the same link twice
    and won't clobber existing links
    """
    # create a backup, taking care to avoid a name conflict
    backup_file = config_file + ".bak"
    i = 0
    while os.access(backup_file, os.R_OK):
        backup_file += str(i)
        i += 1
    cp(config_file, backup_file)
    logger.debug("Copied conf to %s", backup_file)

    try:
        with open(config_file) as f:
            tasks = yaml.load(f)

        # parse the config file see:
        #   https://github.com/anishathalye/dotbot/blob/master/dotbot/dispatcher.py#L19
        new_task = {'link': {}}
        task_is_link = lambda task: 'link' in task
        links_to = [link for task in tasks if 'link' in task
                         for link in task['link']]

        # check the existing links. if the link being created is not already
        # in the list, add it
        links_from = ["." + os.path.split(f)[1] for f in added_files]
        for link_from in links_from:
            link_to = os.path.join("~", link_from)
            if link_to not in links_to:
                new_task['link'][link_to] = link_from
            logger.debug("%s: %s", link_to, link_from)

        # if we actually added any new links, update the config file
        if new_task['link']:
            tasks.append(new_task)
            with open(config_file, 'w') as f:
                yaml.dump(tasks, f, default_flow_style=False)

    except Exception as err:
        logger.debug(err, exc_info=True)
        cp(backup_file, config_file)
    finally:
        os.remove(backup_file)


def parse_args(defaults):
    """
    Parse CLI args, if any
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('directories', nargs='*', default=defaults['repo_root'], metavar='directory',
        help="Directories to restrict the update to (default: entire repository)")
    parser.add_argument('-c', '--config-file', nargs=1, default=[defaults['dotbot_conf']], metavar='file', dest='config_file',
        help="Alternate location of config file (default: '{}')".format(defaults['dotbot_conf']))
    parser.add_argument('-d', '--debug', dest='debug', action='store_true')

    args = parser.parse_args()
    config_file = args.config_file[0]
    directories = args.directories
    if args.debug:
        logger.setLevel(logging.DEBUG)
    return config_file, directories


def main():
    defaults = {}
    defaults['repo_root'] = os.getenv('REPO_ROOT', ".")
    defaults['dotbot_conf'] = os.getenv('DOTBOT_CONF', "dotbot.conf.yaml")

    config_file, directories = parse_args(defaults)

    repo = Repository(defaults['repo_root'])

    added_files = get_added_files(repo, directories)
    if added_files:
        logger.debug("Updating %s", added_files)
        update_dotbot_conf(config_file, added_files)
        repo.index.add(config_file)
    else:
        logger.debug("Nothing to update")


if __name__ == '__main__':
    main()
