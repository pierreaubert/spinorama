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

awk -F',' '{n++; o=o+$2; s=s+$4-$2; if ($4<$2) print "ERROR "$1" " $2" "$4} END {print "Sum Score "o" Sum improvement "s; print "Average score " o/n, "Average delta "s/n}' results_scores.csv
