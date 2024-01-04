#!/bin/awk
# -*- awk -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

BEGIN {
    known["sr"]="Sound &amp; Recording";
    known["pp"]="Production Partner";
    known["audioxpress"]="Audio Xpress";
    known["avnirvana"]="AV Nirvana";
    known["sausalitoaudio"]="Sausalito Audio";
    known["soundstageultra"]="Sound Stage Ultra";
    known["tomvg"]="TomVG";
    # known[""]="";
}
{
    val=toupper(substr($0,1,1));
    name=substr($0,2);

    if ($0 in known) {
       val="";
       name=known[$0];
    } else if (length($0) < 4 ) {
       val="";
       name=toupper($0);
    }

    printf("<option value=\"%s\">%s%s</option>\n", $0, val, name);
}
