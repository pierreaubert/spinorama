#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-21 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

"""
usage: check_meta.py [--help] [--version]

Options:
  --help            display usage()
  --version         script version number
"""
import logging
import sys
import datas.metadata as metadata


def sanity_check_brand(name, speaker):
    if "brand" not in speaker:
        logging.error("brand is not in {0}".format(name))
        return 1
    brand = speaker["brand"]
    if name[0 : len(brand)] != brand:
        logging.error("{0} doesn't start with {1}".format(name, brand))
        return 1
    return 0


def sanity_check_model(name, speaker):
    if "model" not in speaker:
        logging.error("model is not in {0}".format(name))
        return 1
    brand = speaker["brand"]
    model = speaker["model"]
    name_split = model.split(" ")
    if len(name_split) > 0 and name_split[0] == brand:
        logging.warning("{0} does start with brand {1}".format(name, brand))
        return 1
    if name[-len(model) :] != model:
        logging.error("{0} doesn't end with {1}".format(name, model))
        return 1
    return 0


def sanity_check_type(name, speaker):
    valid_types = ("active", "passive")
    if "type" not in speaker:
        logging.error("type is not in {0}".format(name))
        return 1
    thetype = speaker["type"]
    if thetype not in valid_types:
        logging.error(
            "{0}: type {1} is not allowed. Valid items are {2}".format(
                name, thetype, valid_types
            )
        )
        return 1
    return 0


def sanity_check_shape(name, speaker):
    # update src/website/nav_menu if you add a new shape
    valid_shapes = (
        "floorstanders",
        "bookshelves",
        "center",
        "surround",
        "omnidirectional",
        "columns",
        "cbt",
        "outdoor",
        "panel",
        "inwall",
        "soundbar",
        "liveportable",
        "toursound",
        "cinema",
    )
    if "shape" not in speaker:
        logging.error("shape is not in {0}".format(name))
        return 1
    theshape = speaker["shape"]
    if theshape not in valid_shapes:
        logging.error(
            "{0}: shape '{1}' is not allowed. Valid options are {2}".format(
                name, theshape, valid_shapes
            )
        )
        return 1
    return 0


def sanity_check_default_measurement(name, speaker):
    if "default_measurement" not in speaker:
        logging.error("default_measurement is not in {0}".format(name))
        return 1
    default = speaker["default_measurement"]
    if "measurements" in speaker and default not in speaker["measurements"].keys():
        logging.error("{0}: no measurement with key {1}".format(name, default))
        return 1
    return 0


def sanity_check_version_version(term):
    if len(term) >= 2 and (term[0] != "v" or not term[1].isdecimal()):
        return False
    return True


def sanity_check_version_date(term):
    return term.isdecimal()


def sanity_check_version_pattern(term):
    sterm = term.split("x")
    if len(sterm) == 1 and term.isdecimal():
        return True
    # 90x60
    if len(sterm) == 2 and sterm[0].isdecimal() and sterm[1].isdecimal:
        return True
    # h90xv60
    if len(sterm) == 2 and sterm[0][1:].isdecimal() and sterm[1][1:].isdecimal:
        return True
    return False


def sanity_check_version(name, speaker, version):
    # update src/website/assets/search.js is you add a new modifier
    valid_modifiers = (
        # kind
        "vented",
        "sealed",
        "ported",
        "pattern",
        "cardioid",
        "bassreflex",
        "monopole",
        "dipole",
        "fullrange",
        "lowcut",
        # power
        "action",
        "passive",
        # sources
        "klippel",
        "gll",
        # dispersion
        "narrow",
        "medium",
        "wide",
        # grille
        "grilleon",
        "grilleoff",
        # orientation
        "vertical",
        "horizontal",
        # configuration
        "configuration",
    )
    status = 0
    lversion = version.lower()
    if lversion[0:4] == "misc":
        smisc = lversion.split("-")
        if len(smisc) == 3 and smisc[2] not in valid_modifiers:
            logging.error(
                "{}: modifier {} not in {}".format(lversion, smisc[2], valid_modifiers)
            )
            status = 1
    elif lversion[0:6] == "vendor":
        smisc = lversion.split("-")
        for i in range(1, len(smisc)):
            if (
                smisc[i] not in valid_modifiers
                and not sanity_check_version_version(smisc[i])
                and not sanity_check_version_date(smisc[i])
                and not sanity_check_version_pattern(smisc[i])
            ):
                logging.error(
                    "{}: modifier {} not in {}".format(
                        lversion, smisc[i], valid_modifiers
                    )
                )
                status = 1
            if smisc[i] == "configuration":
                # skip all after configuration
                break
    return status


def sanity_check_vendor(vendor):
    if vendor in metadata.origins_info.keys():
        return True
    return False


def sanity_check_measurement(name, speaker, version, measurement):
    status = 0
    if version[0:3] not in ("asr", "pri", "ven", "har", "eac", "mis"):
        logging.error("{0}: key {1} doesn't look correct".format(name, version))
        status = 1
    for k in ("origin", "format"):
        if k not in measurement.keys():
            logging.error(
                "{0}: measurement {1} lack a {2} key".format(name, version, k)
            )
            status = 1

    for k, v in measurement.items():
        if k not in (
            "origin",
            "format",
            "review",
            "reviews",
            "website",
            "misc",
            "symmetry",
            "review_published",
            "notes",
            "quality",
            "parameters",
        ):
            logging.error(
                "{0}: version {1} : {2} is not known".format(name, version, k)
            )
            status = 1
        if k == "origin" and (
            v not in ["ASR", "Misc", "ErinsAudioCorner", "Princeton"]
            and v[0:8] != "Vendors-"
        ):
            logging.error("{0}: origin {1} is not known".format(name, v))
            status = 1
        if k == "origin" and v[0:8] == "Vendors-" and not sanity_check_vendor(v):
            logging.error(
                "{}: origin {} is known but vendor {} is not!".format(name, v, v[8:])
            )
            status = 1
        if k == "format" and v not in [
            "klippel",
            "princeton",
            "webplotdigitizer",
            "rewstextdump",
            "splHVtxt",
        ]:
            logging.error("{0}: format {1} is not known".format(name, v))
            status = 1
        if k == "symmetry" and v not in [
            "coaxial",
            "horizontal",
        ]:
            logging.error("{0}: symmetry {1} is not known".format(name, v))
            status = 1
        if k == "review" and type(v) is not str:
            logging.error("{0}: review {1} is not a string".format(name, v))
            status = 1
        if k == "reviews":
            if type(v) is not dict:
                logging.error("{0}: review {1} is not a dict".format(name, v))
                status = 1
            for ik, iv in v.items():
                if type(iv) is not str:
                    logging.error(
                        "{0}: in reviews {1} review {2} is not a string".format(
                            name, v, iv
                        )
                    )
                    status = 1
        if k == "quality" and v not in ("unknown", "low", "medium", "high"):
            logging.error(
                "{0}: in measurement {1} quality {2} is unknown".format(
                    name,
                    version,
                    v,
                )
            )
            status = 1

    if version[0:3] == "mis" and "quality" not in measurement.keys():
        logging.error(
            "{0}: in measurement {1} quality is required".format(name, version)
        )
        status = 1
    return status


def sanity_check_measurements(name, speaker):
    status = 0
    if "measurements" not in speaker:
        logging.error("measurements is not in {0}".format(name))
        status = 1
    else:
        for version, measurement in speaker["measurements"].items():
            if sanity_check_version(name, speaker, version) != 0:
                status = 1
            if sanity_check_measurement(name, speaker, version, measurement) != 0:
                status = 1
    return status


def sanity_check_speaker(name, speaker):
    if (
        sanity_check_brand(name, speaker) != 0
        or sanity_check_model(name, speaker) != 0
        or sanity_check_type(name, speaker) != 0
        or sanity_check_shape(name, speaker) != 0
        or sanity_check_measurements(name, speaker) != 0
        or sanity_check_default_measurement(name, speaker) != 0
    ):
        return 1
    return 0


def sanity_check_speakers(speakers):
    status = 0
    for name, speaker in speakers.items():
        if sanity_check_speaker(name, speaker) != 0:
            status = 1
    return status


if __name__ == "__main__":
    status = sanity_check_speakers(metadata.speakers_info)
    sys.exit(status)
