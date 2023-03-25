# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import pathlib


def need_update(filename: str, dependencies: list[str]) -> bool:
    """return True if dependencies are newer than filename"""

    # if filename doesn't exist then True
    path = pathlib.Path(filename)
    if not path.is_file():
        return True

    # if file is empty (we store images or json)
    file_stats = path.stat()
    if file_stats.st_size == 0:
        return True

    # if one of the dep is newer than file then True
    for dep in dependencies:
        dep_path = pathlib.Path(dep)
        if not dep_path or dep_path.is_symlink():
            continue
        dep_stats = dep_path.stat()
        if dep_stats.st_mtime > file_stats.st_mtime:
            return True

    return False
