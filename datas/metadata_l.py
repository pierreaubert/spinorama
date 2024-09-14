# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_l: SpeakerDatabase = {
    "L Acoustics 108P": {
        "brand": "L Acoustics",
        "model": "108P",
        "type": "active",
        "price": "7400",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-L Acoustics",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20220924",
            },
        },
    },
    "L Acoustics 112P": {
        "brand": "L Acoustics",
        "model": "112P",
        "type": "active",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-L Acoustics",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20220924",
            },
        },
    },
    "L Acoustics 5XT": {
        "brand": "L Acoustics",
        "model": "5XT",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-L Acoustics",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20240713",
                "specifications": {
                    "dispersion": {
                        "horizontal": 110,
                        "vertical": 110,
                    },
                    "impedance": 16,
                    "SPL": {
                        "peak": 121,
                    },
                    "size": {
                        "height": 165,
                        "width": 165,
                        "depth": 165,
                    },
                    "weight": 3.5,
                },
            },
        },
    },
    "L Acoustics X4i": {
        "brand": "L Acoustics",
        "model": "X4i",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-L Acoustics",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20240713",
                "specifications": {
                    "dispersion": {
                        "horizontal": 110,
                        "vertical": 110,
                    },
                    "impedance": 16,
                    "SPL": {
                        "peak": 116,
                    },
                    "size": {
                        "height": 116,
                        "width": 116,
                        "depth": 99,
                    },
                    "weight": 1.0,
                },
            },
        },
    },
    "L Acoustics X6i": {
        "brand": "L Acoustics",
        "model": "X6i",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-L Acoustics",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20240713",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "impedance": 6,
                    "SPL": {
                        "peak": 123,
                    },
                    "size": {
                        "height": 362,
                        "width": 187,
                        "depth": 170,
                    },
                    "weight": 6.3,
                },
            },
        },
    },
    "L Acoustics X8": {
        "brand": "L Acoustics",
        "model": "X8",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-L Acoustics",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20220924",
            },
        },
    },
    "L Acoustics X12": {
        "brand": "L Acoustics",
        "model": "X12",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-L Acoustics",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20220924",
            },
        },
    },
    "L Acoustics X15 HiQ": {
        "brand": "L Acoustics",
        "model": "X15 HiQ",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-L Acoustics",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20220924",
            },
        },
    },
    "LCM Nearfield Monitor 3-D Printed DIY": {
        "brand": "LCM",
        "model": "Nearfield Monitor 3-D Printed DIY",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/lcm_nearfield_monitor/",
                "review_published": "20220623",
            },
        },
    },
    "LD Systems DDQ10": {
        "brand": "LD Systems",
        "model": "DDQ10",
        "type": "active",
        "price": "1100",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221130",
                "reviews": {
                    "ah": "https://blog.adamhall.com/en/2013/07/25/ld-systems-ddq-10-ddq-12-active-speaker-systems-fairtrade-test-report-by-tools4music/",
                },
                "notes": "measured with broadband noise at 2m. DUT is a DDQ12 with a DDQ Sub 212. It is unclear to me if the measurements are correct",
            },
        },
    },
    "LD Systems DDQ12": {
        "brand": "LD Systems",
        "model": "DDQ12",
        "type": "active",
        "price": "1170",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221130",
                "notes": "measured with broadband noise at 2m. DUT is a DDQ12 with a DDQ Sub 212. It is unclear to me if the measurements are correct",
            },
        },
    },
    "LD Systems DDQ12+Sub": {
        "brand": "LD Systems",
        "model": "DDQ12+Sub",
        "type": "active",
        "price": "3000",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221130",
                "notes": "measured with broadband noise at 2m. DUT is a DDQ12 with a DDQ Sub 212. It is unclear to me if the measurements are correct",
            },
        },
    },
    "LD Systems DDQ15": {
        "brand": "LD Systems",
        "model": "DDQ15",
        "type": "active",
        "price": "1800",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "reviews": {
                    "ah": "https://blog.adamhall.com/de/2014/05/13/ld-systems-ddq-15-und-sub-18-testbericht-von-production-partner/",
                    "pp": "https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.ld-systems.com%2Fen%2Fdownloads%2Ffile%2Fid%2F2145457138&psig=AOvVaw0i9hO28IUZkRnWIyTCpRV4&ust=1670008372681000&source=images&cd=vfe&ved=0CBAQjRxqFwoTCID7qJCQ2fsCFQAAAAAdAAAAABAE",
                },
                "review_published": "20221130",
                "notes": "measured with broadband noise at 2m. DUT is a DDQ12 with a DDQ Sub 212. It is unclear to me if the measurements are correct",
            },
        },
    },
    "LD Systems Stinger 28-A-G3": {
        "brand": "LD Systems",
        "model": "Stinger 28-A-G3",
        "type": "active",
        "price": "770",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221217",
                "notes": "measured with broadband noise at 2m.",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 50,
                    },
                    "SPL": {
                        "peak": 131,
                    },
                    "size": {
                        "height": 756,
                        "width": 270,
                        "depth": 290,
                    },
                    "weight": 20.5,
                },
            },
        },
    },
    "LD Systems Stinger 8-A-G3": {
        "brand": "LD Systems",
        "model": "Stinger 8-A-G3",
        "type": "active",
        "price": "459",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221217",
                "notes": "measured with broadband noise at 2m.",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 50,
                    },
                    "SPL": {
                        "peak": 125,
                    },
                    "size": {
                        "height": 457,
                        "width": 270,
                        "depth": 290,
                    },
                    "weight": 10.5,
                },
            },
        },
    },
    "LD Systems Stinger 10-A-G3": {
        "brand": "LD Systems",
        "model": "Stinger 10-A-G3",
        "type": "active",
        "price": "500",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221217",
                "notes": "measured with broadband noise at 2m.",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 50,
                    },
                    "SPL": {
                        "peak": 127,
                    },
                    "size": {
                        "height": 527,
                        "width": 325,
                        "depth": 318,
                    },
                    "weight": 12.7,
                },
            },
        },
    },
    "LD Systems Stinger 12-A-G3": {
        "brand": "LD Systems",
        "model": "Stinger 12-A-G3",
        "type": "active",
        "price": "745",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221217",
                "notes": "measured with broadband noise at 2m.",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 50,
                    },
                    "SPL": {
                        "peak": 131,
                    },
                    "size": {
                        "height": 627,
                        "width": 390,
                        "depth": 377,
                    },
                    "weight": 20.1,
                },
            },
        },
    },
    "LD Systems Stinger 15-A-G3": {
        "brand": "LD Systems",
        "model": "Stinger 15-A-G3",
        "type": "active",
        "price": "839",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-LD Systems",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221217",
                "notes": "measured with broadband noise at 2m.",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 50,
                    },
                    "SPL": {
                        "peak": 133,
                    },
                    "size": {
                        "height": 737,
                        "width": 480,
                        "depth": 455,
                    },
                    "weight": 26.8,
                },
            },
        },
    },
    "Linkwitz LXMini DIY": {
        "brand": "Linkwitz",
        "model": "LXMini DIY",
        "type": "active",
        "price": "800",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/linkwitz_lx_mini/",
                    "yt": "https://youtu.be/x29dab0p_XE",
                },
                "review_published": "20220801",
            },
        },
    },
    "LOGProfessional Alpha": {
        "brand": "LOGProfessional",
        "model": "Alpha",
        "type": "active",
        "price": "5930",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "misc-sr",
        "measurements": {
            "misc-sr": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "medium",
                "reviews": {
                    "snr": "https://www.soundandrecording.de/allgemein/log-professional-alpha-2-wege-nahfeldmonitor-im-test/",
                },
                "review_published": "20240914",
                "specifications": {
                    "size": {
                        "height": 340,
                        "width": 220,
                        "depth": 220,
                    },
                    "weight": 7.0,
                },
            },
        },
    },
    "LYX SPA8PAS": {
        "brand": "LYX",
        "model": "SPA8PAS",
        "type": "passive",
        "price": "100",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "misc-mtg90",
        "measurements": {
            "misc-mtg90": {
                "origin": "Misc",
                "format": "rew_text_dump",
                "quality": "low",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/worst-measuring-loudspeaker.11394/page-8#post-945725",
                "review_published": "20211019",
            },
        },
    },
}
