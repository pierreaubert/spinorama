#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

"""usage: check_meta.py [--help] [--version].

Options:
  --help            display usage()
  --version         script version number
"""

import datetime
import logging
import sys

from datas import metadata, Speaker, SpeakerDatabase, Measurement


def sanity_check_brand(name: str, speaker: Speaker) -> int:
    """check if name include brand"""
    if "brand" not in speaker:
        logging.error("brand is not in %s", name)
        return 1
    brand = speaker["brand"]
    if name[0 : len(brand)] != brand:
        logging.error("%s doesn't start with %s", name, brand)
        return 1
    return 0


VALID_AMOUNTS = ("each", "pair")


def sanity_check_amount(name: str, speaker: Speaker) -> int:
    """check if name include brand"""
    #    if "amount" not in speaker and "price" in speaker:
    #        sprice = speaker["price"]
    #        try:
    #            price = int(sprice)
    #            if price>0:
    #                logging.error("amount is not in %s but price is %d", name, price)
    #                return 1
    #        except ValueError:
    #            pass
    if "amount" in speaker:
        amount = speaker["amount"]
        if amount not in VALID_AMOUNTS:
            logging.error(
                "%s: amount %s is not allowed. Valid amounts are (%s)",
                name,
                amount,
                ",".join(VALID_AMOUNTS),
            )
            return 1
    return 0


def sanity_check_model(name: str, speaker: Speaker) -> int:
    """check if name include model"""
    if "model" not in speaker:
        logging.error("model is not in %s", name)
        return 1
    brand = speaker["brand"]
    model = speaker["model"]
    name_split = model.split(" ")
    if len(name_split) > 0 and name_split[0] == brand:
        logging.warning("%s does start with brand %s", name, brand)
        return 1
    if name[-len(model) :] != model:
        logging.error("%s doesn't end with %s", name, model)
        return 1
    return 0


VALID_TYPES = ("active", "passive")


def sanity_check_type(name: str, speaker: Speaker) -> int:
    """check if type is valid"""
    if "type" not in speaker:
        logging.error("type is not in %s", name)
        return 1
    thetype = speaker["type"]
    if thetype not in VALID_TYPES:
        logging.error(
            "%s: type %s is not allowed. Valid items are (%s)", name, thetype, ",".join(VALID_TYPES)
        )
        return 1
    return 0


# update src/website/nav_menu if you add a new shape
VALID_SHAPES = (
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


def sanity_check_shape(name: str, speaker: Speaker) -> int:
    """check if shape is valid"""
    if "shape" not in speaker:
        logging.error("shape is not in %s", name)
        return 1
    theshape = speaker["shape"]
    if theshape not in VALID_SHAPES:
        logging.error(
            "%s: shape '%s' is not allowed. Valid options are (%s)",
            name,
            theshape,
            ", ".join(VALID_SHAPES),
        )
        return 1
    if theshape == "center":
        if "amount" not in speaker:
            logging.error("shape is center but amount not in %s", name)
            return 1
        amount = speaker["amount"]
        if amount != "each":
            logging.error(
                "shape is center and amount must be each; check amount for %s please!", name
            )
            return 1
    return 0


def sanity_check_default_measurement(name: str, speaker: Speaker) -> int:
    """check that we have a default key"""
    if "default_measurement" not in speaker:
        logging.error("default_measurement is not in %s", name)
        return 1
    default = speaker["default_measurement"]
    if "measurements" in speaker and default not in speaker["measurements"]:
        logging.error("%s: no measurement with key %s", name, default)
        return 1
    return 0


TERM_MIN_SIZE = 2


def sanity_check_version_version(term: str) -> bool:
    """check that version match some pattern"""
    if len(term) >= TERM_MIN_SIZE and (term[0] != "v" or not term[1].isdecimal()):
        return False
    return True


def sanity_check_version_date(term: str) -> bool:
    """check that version match some date"""
    return term.isdecimal()


PATTERN_LENGTH_1 = 1
PATTERN_LENGTH_2 = 2


def sanity_check_version_pattern(term: str) -> bool:
    """check that version match some pattern"""
    sterm = term.split("x")
    if len(sterm) == PATTERN_LENGTH_1 and term.isdecimal():
        return True
    # 90x60
    if len(sterm) == PATTERN_LENGTH_2 and sterm[0].isdecimal() and sterm[1].isdecimal:
        return True
    # h90xv60
    if len(sterm) == PATTERN_LENGTH_2 and sterm[0][1:].isdecimal() and sterm[1][1:].isdecimal:
        return True
    return False


VALID_MODIFIERS = (
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
    # speaker
    "dome",
    "ribbon",
    "tweeter",
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
    # specific for Devialet Phantom
    "vtree",
    "vgecko",
    "vpod",
)


VERSION_PATTERN_LENGTH = 3


def sanity_check_version(version: str) -> int:
    """check that version match some patterns"""
    # update src/website/assets/search.js is you add a new modifier
    status = 0
    lversion = version.lower()
    if lversion[0:4] == "misc":
        smisc = lversion.split("-")
        if len(smisc) == VERSION_PATTERN_LENGTH and smisc[2] not in VALID_MODIFIERS:
            logging.error(
                "%s: modifier %s not in (%s)", lversion, smisc[2], ", ".join(VALID_MODIFIERS)
            )
            status = 1
    elif lversion[0:6] == "vendor":
        smisc = lversion.split("-")
        for i in range(1, len(smisc)):
            if (
                smisc[i] not in VALID_MODIFIERS
                and not sanity_check_version_version(smisc[i])
                and not sanity_check_version_date(smisc[i])
                and not sanity_check_version_pattern(smisc[i])
            ):
                logging.error(
                    "%s: modifier %s not in %s", lversion, smisc[i], ", ".join(VALID_MODIFIERS)
                )
                status = 1
            if smisc[i] == "configuration":
                # skip all after configuration
                break
    return status


def sanity_check_vendor(vendor: str) -> bool:
    """check that vendor is known"""
    if vendor in metadata.origins_info:
        return True
    return False


VALID_SPECIFICATIONS = (
    "dispersion",
    "sensitivity",
    "impedance",
    "SPL",
    "size",
    "weight",
)

VALID_DIMS = ("height", "width", "depth")

VALID_ANGLE_MIN = 0
VALID_ANGLE_MAX = 180

VALID_SENSITIVY_MIN = 20
VALID_SENSITIVY_MAX = 150

VALID_IMPEDANCE_MIN = 0
VALID_IMPEDANCE_MAX = 50

VALID_SPL_MIN = 0
VALID_SPL_MAX = 160

VALID_DIM_MIN = 0
VALID_DIM_MAX = 2500

VALID_WEIGTH_MIN = 0
VALID_WEIGTH_MAX = 500


def sanity_check_specifications(name: str, version: str, specs: dict) -> int:
    """Check that the specs block is valid"""
    status = 0
    for k, v in specs.items():
        if k not in VALID_SPECIFICATIONS:
            logging.error(
                "%s: measurement %s key %s is not in %s",
                name,
                version,
                k,
                ", ".join(VALID_SPECIFICATIONS),
            )
            status = 1

        if k == "dispersion":
            for direction, angle in v.items():
                if direction not in ("horizontal", "vertical"):
                    logging.error(
                        "%s: measurement %s direction %s is not in ('horizontal', 'vertical')",
                        name,
                        version,
                        direction,
                    )
                    status = 1
                try:
                    fangle = float(angle)
                    if fangle < VALID_ANGLE_MIN or fangle > VALID_ANGLE_MAX:
                        logging.error(
                            "%s: measurement %s angle %s is not in ]%d, %d]",
                            name,
                            version,
                            angle,
                            VALID_ANGLE_MIN,
                            VALID_ANGLE_MAX,
                        )
                        status = 1
                except ValueError:
                    logging.exception(
                        "%s: measurement %s angle %s is not an int or a float",
                        name,
                        version,
                        angle,
                    )
                    status = 1

        if k == "sensitivity":
            try:
                fsensitivity = float(v)
                if fsensitivity < VALID_SENSITIVY_MIN or fsensitivity >= VALID_SENSITIVY_MAX:
                    logging.error(
                        "%s: measurement %s sensitivity %s is not in ]%d, %d]",
                        name,
                        version,
                        fsensitivity,
                        VALID_SENSITIVY_MIN,
                        VALID_SENSITIVY_MAX,
                    )
                    status = 1
            except ValueError:
                logging.exception(
                    "%s: measurement %s sensitivity %s is not an int or a float",
                    name,
                    version,
                    v,
                )
                status = 1

        if k == "impedance":
            try:
                fimpedance = float(v)
                if fimpedance <= VALID_IMPEDANCE_MIN or fimpedance >= VALID_IMPEDANCE_MAX:
                    logging.error(
                        "%s: measurement %s impedance %s is not in ]%d, %d]",
                        name,
                        version,
                        v,
                        VALID_IMPEDANCE_MIN,
                        VALID_IMPEDANCE_MAX,
                    )
                    status = 1
            except ValueError:
                logging.exception(
                    "%s: measurement %s impedance is not an int or a float", name, version
                )
                status = 1

        if k == "SPL":
            for state, spl in v.items():
                if state not in (
                    "max",
                    "continuous",
                    "peak",
                    "m_noise",
                    "b_noise",
                    "pink_noise",
                ):
                    logging.error(
                        "%s: measurement %s SPL parameter %s is not in ('mean', 'continous', 'peak')",
                        name,
                        version,
                        state,
                    )
                    status = 1
                try:
                    fspl = float(spl)
                    if fspl < VALID_SPL_MIN or fspl >= VALID_SPL_MAX:  # for Danley's :)
                        logging.error(
                            "%s: measurement %s spl %s is not in ]%d, %d]",
                            name,
                            version,
                            spl,
                            VALID_SPL_MIN,
                            VALID_SPL_MAX,
                        )
                        status = 1
                except ValueError:
                    logging.exception(
                        "%s: measurement %s spl %s is not an int or a float", name, version, spl
                    )
                    status = 1

        if k == "size":
            for dim, m_m in v.items():
                if dim not in VALID_DIMS:
                    logging.error(
                        "%s: measurement %s SPL parameter %s is not in %s",
                        name,
                        version,
                        dim,
                        ", ".join(VALID_DIMS),
                    )
                    status = 1
                try:
                    fm_m = float(m_m)
                    if fm_m < VALID_DIM_MIN or fm_m >= VALID_DIM_MAX:  # for Danley's :)
                        logging.error(
                            "%s: measurement %s m_m %s is not in ]0, 160]", name, version, m_m
                        )
                        status = 1
                except ValueError:
                    logging.exception(
                        "%s: measurement %s m_m %s is not an int or a float", name, version, m_m
                    )
                    status = 1

        if k == "weight":
            try:
                fweight = float(v)
                if (
                    fweight <= VALID_WEIGTH_MIN or fweight >= VALID_WEIGTH_MAX
                ):  # there are some very large beast
                    logging.error(
                        "%s: measurement %s weight %s is not in ]0, 50]", name, version, fweight
                    )
                    status = 1
            except ValueError:
                logging.exception(
                    "%s: measurement %s weight %s is not an int or a float", name, version, v
                )
                status = 1

    return status


MEASUREMENT_KNOWN_KEYS = (
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
    "specifications",
    "extras",
    "data_acquisition",
)

FORMAT_KNOWN_KEYS = (
    "klippel",
    "princeton",
    "webplotdigitizer",
    "rew_text_dump",
    "spl_hv_txt",
    "gll_hv_txt",
)


def sanity_check_measurement(name: str, version: str, measurement: Measurement) -> int:
    """Check each measurement"""
    status = 0
    if version[0:3] not in ("asr", "pri", "ven", "har", "eac", "mis", "aud"):
        logging.error("%s: key %s doesn't look correct", name, version)
        status = 1
    for k in ("origin", "format"):
        if k not in measurement:
            logging.error("%s: measurement %s lack a %s key", name, version, k)
            status = 1

    for k, v in measurement.items():
        if k not in MEASUREMENT_KNOWN_KEYS:
            logging.error("%s: version %s : %s is not known", name, version, k)
            status = 1
            continue
        if k == "origin" and (
            isinstance(v, str)
            and v not in ["ASR", "Misc", "ErinsAudioCorner", "Princeton"]
            and v[0:8] != "Vendors-"
        ):
            logging.error("%s: origin %s is not known", name, v)
            status = 1
            continue
        if (
            k == "origin"
            and isinstance(v, str)
            and v[0:8] == "Vendors-"
            and not sanity_check_vendor(v)
        ):
            logging.error("%s: origin %s is known but vendor %s is not!", name, v, v[8:])
            status = 1
            continue
        if k == "format" and v not in FORMAT_KNOWN_KEYS:
            logging.error("%s: format %s is not known", name, v)
            status = 1
            continue
        if k == "symmetry" and v not in [
            "coaxial",
            "horizontal",
            "vertical",
        ]:
            logging.error("%s: symmetry %s is not known", name, v)
            status = 1
            continue
        if k == "review" and not isinstance(v, str):
            logging.error("%s: review %s is not a string", name, v)
            status = 1
            continue
        if k == "reviews":
            if not isinstance(v, dict):
                logging.error("%s: review %s is not a dict", name, v)
                status = 1
                continue
            for _, i_v in v.items():
                if not isinstance(i_v, str):
                    logging.error("%s: in reviews %s review %s is not a string", name, v, i_v)
                    status = 1
            continue
        if k == "quality" and v not in ("unknown", "low", "medium", "high"):
            logging.error(
                "%s: in measurement %s quality %s is unknown",
                name,
                version,
                v,
            )
            status = 1
            continue

        if (
            k == "specifications"
            and isinstance(v, dict)
            and sanity_check_specifications(name, version, v) != 0
        ):
            logging.error(
                "%s: in measurement %s specifications %s is incorrect",
                name,
                version,
                v,
            )
            status = 1
            continue

        if k == "review_published" and (not isinstance(v, str) or len(v) != 8):
            if isinstance(v, str):
                try:
                    datetime.date.fromisoformat(v)
                except ValueError:
                    logging.error(
                        "%s: in measurement %s review_published %s is not a valid ISO date",
                        name,
                        version,
                        v,
                    )
                else:
                    logging.error(
                        "%s: in measurement %s review_published %s is incorrect (len is %d and should be 8)",
                        name,
                        version,
                        v,
                        len(v),
                    )
                status = 1
            continue

    if version[0:3] == "mis" and "quality" not in measurement:
        logging.error("%s: in measurement %s quality is required", name, version)
        status = 1
    return status


def sanity_check_measurements(name: str, speaker: Speaker) -> int:
    """Check all measurements for a speaker"""
    status = 0
    if "measurements" not in speaker:
        logging.error("measurements is not in %s", name)
        status = 1
    else:
        for version, measurement in speaker["measurements"].items():
            if sanity_check_version(version) != 0:
                status = 1
            if sanity_check_measurement(name, version, measurement) != 0:
                status = 1
    return status


def sanity_check_speaker(name: str, speaker: Speaker) -> int:
    """Check a speaker description"""
    if (
        sanity_check_brand(name, speaker) != 0
        or sanity_check_model(name, speaker) != 0
        or sanity_check_type(name, speaker) != 0
        or sanity_check_shape(name, speaker) != 0
        or sanity_check_amount(name, speaker) != 0
        or sanity_check_measurements(name, speaker) != 0
        or sanity_check_default_measurement(name, speaker) != 0
    ):
        logging.error("speaker failed %s", name)
        return 1
    return 0


def sanity_check_speakers(speakers: SpeakerDatabase) -> int:
    """Check all speakers description"""
    status = 0
    for name, speaker in speakers.items():
        if sanity_check_speaker(name, speaker) != 0:
            status += 1
    return status


if __name__ == "__main__":
    MAIN_STATUS = sanity_check_speakers(metadata.speakers_info)
    sys.exit(MAIN_STATUS)
