# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_r: SpeakerDatabase = {
    "Radiant Acoustics Clarity 6.2": {
        "skip": True,
        "brand": "Radiant Acoustics",
        "model": "Clarity 6.2",
        "type": "passive",
        "price": "4000",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/radiant_acoustics_clarity62/",
                    "yt": "https://youtu.be/wV52ek8lUWc?si=Flb48-ZXMJP3ctFd",
                },
                "review_published": "2024xxxx",
                "specifications": {
                    "sensitivity": 85,
                    "impedance": 4,
                    "size": {
                        "height": 364,
                        "width": 222,
                        "depth": 266,
                    },
                    "weight": 12.45,
                },
            },
        },
    },
    "Rauna Freja": {
        "brand": "Rauna",
        "model": "Freja",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "misc-mab",
        "measurements": {
            "misc-mab": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/rauna-freja-vintage-2-way-loudspeaker-measurements.50093/page-2#post-2117440",
                },
                "review_published": "20241023",
                "specifications": {
                    "sensitivity": 88,
                    "impedance": 7,
                    "size": {
                        "height": 805,
                        "width": 280,
                        "depth": 320,
                    },
                    "weight": 33.0,
                },
            },
        },
    },
    "RBH Sound R-5": {
        "brand": "RBH Sound",
        "model": "R-5",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "misc-audioholics",
        "measurements": {
            "misc-audioholics": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://www.audioholics.com/bookshelf-speaker-reviews/rbh-r-5/conclusion",
            },
        },
    },
    "RCF ART 708-A MK4": {
        "brand": "RCF",
        "model": "ART 708-A MK4",
        "type": "active",
        "price": "",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x70",
        "measurements": {
            "vendor-pattern-90x70": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230114",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 70,
                    },
                    "SPL": {
                        "peak": 127,
                    },
                    "size": {
                        "height": 480,
                        "width": 291,
                        "depth": 276,
                    },
                    "weight": 10.4,
                },
            },
        },
    },
    "RCF ART 710-A MK4": {
        "skip": True,  # missing gll file on website
        "brand": "RCF",
        "model": "ART 710-A MK4",
        "type": "active",
        "price": "469",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x70",
        "measurements": {
            "vendor-pattern-90x70": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230114",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 70,
                    },
                    "SPL": {
                        "peak": 129,
                    },
                    "size": {
                        "height": 548,
                        "width": 340,
                        "depth": 305,
                    },
                    "weight": 14.2,
                },
            },
        },
    },
    "RCF ART 712-A MK4": {
        "brand": "RCF",
        "model": "ART 712-A MK4",
        "type": "active",
        "price": "509",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230114",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 129,
                    },
                    "size": {
                        "height": 637,
                        "width": 387,
                        "depth": 363,
                    },
                    "weight": 17.8,
                },
            },
        },
    },
    "RCF ART 715-A MK4": {
        "brand": "RCF",
        "model": "ART 715-A MK4",
        "type": "active",
        "price": "500",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221107",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 130,
                    },
                    "size": {
                        "height": 708,
                        "width": 437,
                        "depth": 389,
                    },
                    "weight": 19.6,
                },
            },
        },
    },
    "RCF ART 725-A MK4": {
        "brand": "RCF",
        "model": "ART 725-A MK4",
        "type": "active",
        "price": "",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230114",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 133,
                    },
                    "size": {
                        "height": 708,
                        "width": 437,
                        "depth": 389,
                    },
                    "weight": 19.6,
                },
            },
        },
    },
    "RCF ART 732-A MK4": {
        "brand": "RCF",
        "model": "ART 732-A MK4",
        "type": "active",
        "price": "",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230114",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 131,
                    },
                    "size": {
                        "height": 637,
                        "width": 384,
                        "depth": 363,
                    },
                    "weight": 17.8,
                },
            },
        },
    },
    "RCF ART 735-A MK4": {
        "brand": "RCF",
        "model": "ART 735-A MK4",
        "type": "active",
        "price": "888",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230114",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 132,
                    },
                    "size": {
                        "height": 708,
                        "width": 437,
                        "depth": 389,
                    },
                    "weight": 21.4,
                },
            },
        },
    },
    "RCF ART 745-A MK4": {
        "brand": "RCF",
        "model": "ART 745-A MK4",
        "type": "active",
        "price": "1245",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230114",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 133,
                    },
                    "size": {
                        "height": 708,
                        "width": 437,
                        "depth": 389,
                    },
                    "weight": 18.8,
                },
            },
        },
    },
    "RCF ART 910-A": {
        "brand": "RCF",
        "model": "ART 910-A",
        "type": "active",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x60",
        "measurements": {
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230113",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 130,
                    },
                    "size": {
                        "height": 572,
                        "width": 330,
                        "depth": 310,
                    },
                    "weight": 15.8,
                },
            },
        },
    },
    "RCF ART 912-A": {
        "brand": "RCF",
        "model": "ART 912-A",
        "type": "active",
        "price": "599",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x60",
        "measurements": {
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230113",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 130,
                    },
                    "size": {
                        "height": 642,
                        "width": 370,
                        "depth": 363,
                    },
                    "weight": 19.0,
                },
            },
        },
    },
    "RCF ART 932-A": {
        "brand": "RCF",
        "model": "ART 932-A",
        "type": "active",
        "price": "1800",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x60",
        "measurements": {
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230113",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 131,
                    },
                    "size": {
                        "height": 642,
                        "width": 370,
                        "depth": 363,
                    },
                    "weight": 18.8,
                },
            },
        },
    },
    "RCF ART 935-A": {
        "brand": "RCF",
        "model": "ART 935-A",
        "type": "active",
        "price": "2030",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x60",
        "measurements": {
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230113",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 133,
                    },
                    "size": {
                        "height": 717,
                        "width": 415,
                        "depth": 410,
                    },
                    "weight": 24.2,
                },
            },
        },
    },
    "RCF ART 945-A": {
        "brand": "RCF",
        "model": "ART 945-A",
        "type": "active",
        "price": "2800",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "misc-pp",
        "measurements": {
            "misc-pp": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://www.production-partner.de/test/test-rcf-art-945-a/",
                "review_published": "20211215",
            },
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review": "https://www.production-partner.de/test/test-rcf-art-945-a/",
                "review_published": "20221107",
                "notes": "the quality of the data is unknown: it looks incorrect around 1k Hz if we compare to the results from the German magazine Production Partner",
            },
        },
    },
    "RCF Ayra Pro5": {
        "brand": "RCF",
        "model": "Ayra Pro5",
        "type": "active",
        "price": "300",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/rcf-ayra-pro5-review-powered-monitor.31777/",
                    "yt": "https://youtu.be/-igZ8X81h-k",
                },
                "review_published": "20220317",
            },
        },
    },
    "RCF H1315 WP": {
        "brand": "RCF",
        "model": "H1315 WP",
        "type": "active",
        "price": "",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-60x40",
        "measurements": {
            "vendor-pattern-60x40": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221107",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 40,
                    },
                    "impedance": 8,
                    "SPL": {
                        "peak": 136,
                    },
                    "size": {
                        "height": 890,
                        "width": 520,
                        "depth": 632,
                    },
                    "weight": 51.0,
                },
            },
        },
    },
    "RCF HD 10-A MK5": {
        "brand": "RCF",
        "model": "HD 10-A MK5",
        "type": "active",
        "price": "469",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230115",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 128,
                    },
                    "size": {
                        "height": 572,
                        "width": 303,
                        "depth": 303,
                    },
                    "weight": 11.8,
                },
            },
        },
    },
    "RCF HD 12-A MK5": {
        "brand": "RCF",
        "model": "HD 12-A MK5",
        "type": "active",
        "price": "600",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230115",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 130,
                    },
                    "size": {
                        "height": 647,
                        "width": 380,
                        "depth": 380,
                    },
                    "weight": 18.3,
                },
            },
        },
    },
    "RCF NX 910-A": {
        "brand": "RCF",
        "model": "NX 910-A",
        "type": "active",
        "price": "533",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x60",
        "measurements": {
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230113",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 130,
                    },
                    "size": {
                        "height": 510,
                        "width": 295,
                        "depth": 333,
                    },
                    "weight": 16.4,
                },
            },
        },
    },
    "RCF NX 912-A": {
        "brand": "RCF",
        "model": "NX 912-A",
        "type": "active",
        "price": "899",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x60",
        "measurements": {
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230113",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 130,
                    },
                    "size": {
                        "height": 620,
                        "width": 362,
                        "depth": 405,
                    },
                    "weight": 20.8,
                },
            },
        },
    },
    "RCF NX 915-A": {
        "brand": "RCF",
        "model": "NX 915-A",
        "type": "active",
        "price": "",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x60",
        "measurements": {
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230113",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 131,
                    },
                    "size": {
                        "height": 705,
                        "width": 420,
                        "depth": 451,
                    },
                    "weight": 24.1,
                },
            },
        },
    },
    "RCF NX 985-A": {
        "brand": "RCF",
        "model": "NX 985-A",
        "type": "active",
        "price": "1840",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x60",
        "measurements": {
            "vendor-pattern-100x60": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230113",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 138,
                    },
                    "size": {
                        "height": 1075,
                        "width": 461,
                        "depth": 475,
                    },
                    "weight": 45.0,
                },
            },
        },
    },
    "RCF NXL 14-A": {
        "brand": "RCF",
        "model": "NXL 14-A",
        "type": "active",
        "price": "1200",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x70",
        "measurements": {
            "vendor-pattern-100x70": {
                "origin": "Vendors-RCF",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20241105",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 70,
                    },
                    "SPL": {
                        "peak": 128,
                    },
                    "size": {
                        "height": 576,
                        "width": 197,
                        "depth": 270,
                    },
                    "weight": 12.8,
                },
            },
        },
    },
    "Realistic MC-1000": {
        "brand": "Realistic",
        "model": "MC-1000",
        "type": "passive",
        "price": "60",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/mc-1000-best-speaker-in-the-world.11283/",
                "review_published": "20200206",
            },
        },
    },
    "Realistic Tandy Minimus 7": {
        "brand": "Realistic",
        "model": "Tandy Minimus 7",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
        "default_measurement": "misc-mab",
        "measurements": {
            "misc-mab": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/realistic-minimus-7-measurements.57184/",
                    "amg": "https://archimago.blogspot.com/2021/01/retro-measure-radio-shack-realistic.html",
                },
                "review_published": "20241023",
            },
            "misc-archimago": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
            },
        },
    },
    "Reflector Audio Square Two": {
        "brand": "Reflector Audio",
        "model": "Square Two",
        "type": "active",
        "price": "4000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Reflector Audio",
                "format": "webplotdigitizer",
                "quality": "medium",
                "reviews": {
                    "sar": "https://www.soundandrecording.de/equipment/reflector-audio-koaxialer-hochleistungs-midfield-monitor-im-test/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/detailed-measurements-and-spinorama-of-reflector-audio-square-two-2-way-coaxial-horn-monitor-with-4x-5-woofers.29072/",
                },
                "review_published": "20211217",
            },
        },
    },
    "Revel C10": {
        "brand": "Revel",
        "model": "C10",
        "type": "passive",
        "price": "",
        "shape": "center",
        "amount": "each",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-concerta-c10-review-center-speaker.28918/",
                "review_published": "20211211",
            },
        },
    },
    "Revel C205": {
        "brand": "Revel",
        "model": "C205",
        "type": "passive",
        "price": "",
        "amount": "each",
        "shape": "center",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
        },
    },
    "Revel C208": {
        "brand": "Revel",
        "model": "C208",
        "type": "passive",
        "price": "2000",
        "shape": "center",
        "amount": "each",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-c208-review-center-speaker.21303/",
                "review_published": "20210313",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
        },
    },
    "Revel C25": {
        "brand": "Revel",
        "model": "C25",
        "type": "passive",
        "shape": "center",
        "price": "825",
        "amount": "each",
        "default_measurement": "asr-horizontal",
        "measurements": {
            "asr-vertical": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-concerta2-c25-review-center-speaker.29499/",
                "review_published": "20211231",
            },
            "asr-horizontal": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-concerta2-c25-review-center-speaker.29499/",
                "review_published": "20211231",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
        },
    },
    "Revel C426Be": {
        "brand": "Revel",
        "model": "C426Be",
        "type": "passive",
        "price": "",
        "shape": "center",
        "amount": "each",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
        },
    },
    "Revel C52": {
        "brand": "Revel",
        "model": "C52",
        "type": "passive",
        "price": "2500",
        "shape": "center",
        "amount": "each",
        "default_measurement": "asr-vertical",
        "measurements": {
            "asr-vertical": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-c52-speaker-review-and-measurements.10934/",
                "review_published": "20200117",
            },
            "asr-horizontal": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-c52-speaker-review-and-measurements.10934/",
                "review_published": "20200117",
            },
        },
    },
    "Revel F35": {
        "brand": "Revel",
        "model": "F35",
        "type": "passive",
        "price": "1600",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "asr-v2-20210415",
        "measurements": {
            "asr-v2-20210415": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr-v1": "https://www.audiosciencereview.com/forum/index.php?threads/revel-f35-speaker-review.12053/",
                    "asr-v2": "https://www.audiosciencereview.com/forum/index.php?threads/bass-response-correction-for-klippel-nfs-measurements.22493/",
                },
                "notes": "Second measurement with bass corrections",
                "review_published": "20200314",
            },
            "asr-v1-20200315": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-f35-speaker-review.12053/",
                "review_published": "20200314",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
        },
    },
    "Revel F36": {
        "brand": "Revel",
        "model": "F36",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
        },
    },
    "Revel F206": {
        "brand": "Revel",
        "model": "F206",
        "type": "passive",
        "price": "2500",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/revel-f206-tower-speaker-review.53691/",
                },
                "review_published": "20240411",
                "specifications": {
                    "sensitivity": 88,
                    "impedance": 8,
                    "size": {
                        "height": 1052,
                        "width": 249,
                        "depth": 347,
                    },
                    "weight": 26.0,
                },
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
        },
    },
    "Revel F208": {
        "brand": "Revel",
        "model": "F208",
        "type": "passive",
        "price": "5000",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "asr-v2-20210519",
        "measurements": {
            "asr-v2-20210519": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-f208-tower-speaker-review.13192/",
                "review_published": "20200508",
            },
            "asr-v1-20200508": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-f208-tower-speaker-review.13192/",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
        },
    },
    "Revel F226be": {
        "brand": "Revel",
        "model": "F226be",
        "type": "passive",
        "price": "2900",
        "shape": "floorstanders",
        "amount": "each",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "spl_hv_txt",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/revel_f226be/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/revel-performabe-f226be-floorstanding-speaker-review.16702/",
                },
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
        },
    },
    "Revel F228Be": {
        "brand": "Revel",
        "model": "F228Be",
        "type": "passive",
        "price": "10000",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/revel-f228be-review-speaker.23659/",
                    "stp": "https://www.stereophile.com/content/revel-performa-f228be-loudspeaker",
                },
                "review_published": "20210523",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
        },
    },
    "Revel F328be": {
        "brand": "Revel",
        "model": "F328be",
        "type": "passive",
        "price": "16000",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "asr-v2-20210415",
        "measurements": {
            "asr-v2-20210415": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr-v1": "https://www.audiosciencereview.com/forum/index.php?threads/revel-f328be-speaker-review.17443/",
                    "asr-v2": "https://www.audiosciencereview.com/forum/index.php?threads/bass-response-correction-for-klippel-nfs-measurements.22493/",
                },
                "review_published": "20210415",
                "notes": "Second measurement with bass corrections",
            },
            "asr-v1-20201110": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-f328be-speaker-review.17443/",
                "review_published": "20201110",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
        },
    },
    "Revel M126Be": {
        "brand": "Revel",
        "model": "M126Be",
        "type": "passive",
        "price": "3300",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/revel_m126be/",
                    "yt": "https://youtu.be/KecbtoerdE0",
                },
                "review_published": "20231219",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
            "misc-audioholics": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://www.audioholics.com/bookshelf-speaker-reviews/revel-performa-m126be/conclusion",
            },
        },
    },
    "Revel Ultima Studio": {
        "brand": "Revel",
        "model": "Ultima Studio",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
            },
        },
    },
    "Revel Ultima Salon": {
        "brand": "Revel",
        "model": "Ultima Salon",
        "type": "passive",
        "price": "",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
            },
        },
    },
    "Revel Ultima2 Gem2": {
        "brand": "Revel",
        "model": "Ultima2 Gem2",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-ultima.html",
            },
        },
    },
    "Revel Ultima2 Salon2": {
        "brand": "Revel",
        "model": "Ultima2 Salon2",
        "type": "passive",
        "price": "",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "harman-v2-2017",
        "measurements": {
            "harman-v1-2007": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
            "harman-v2-2017": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
        },
    },
    "Revel Ultima2 Studio2": {
        "brand": "Revel",
        "model": "Ultima2 Studio2",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-ultima.html",
            },
        },
    },
    "Revel Ultima2 Voice2": {
        "brand": "Revel",
        "model": "Ultima2 Voice2",
        "type": "passive",
        "price": "",
        "shape": "center",
        "amount": "each",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-ultima.html",
            },
        },
    },
    "Revel M105": {
        "brand": "Revel",
        "model": "M105",
        "type": "passive",
        "price": "1500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-m105-bookshelf-speaker-review.14745/",
                "review_published": "20200716",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
        },
    },
    "Revel M106": {
        "brand": "Revel",
        "model": "M106",
        "type": "passive",
        "price": "4000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-m106-bookshelf-speaker-review.14363/",
                "review_published": "20200626",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://speakerdata2034.blogspot.com/2019/03/spinorama-data-revel-home.html",
            },
        },
    },
    "Revel M16": {
        "brand": "Revel",
        "model": "M16",
        "type": "passive",
        "price": "900",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/revel-m16-speaker-review.11884/",
                    "asr-dominikz": "https://www.audiosciencereview.com/forum/index.php?threads/revel-m16-quasi-anechoic-spinorama-and-misc-measurements.27076/#post-928962",
                    "asr-ageve": "https://www.audiosciencereview.com/forum/index.php?threads/revel-m16-spinorama-measurements-cta-2034.58370/",
                },
                "review_published": "20200305",
                "specifications": {
                    "sensitivity": 86,
                    "impedance": 6,
                    "size": {
                        "height": 370,
                        "width": 220,
                        "depth": 370,
                    },
                    "weight": 7.26,
                },
            },
            "misc-dominikz": {
                "origin": "Misc",
                "format": "rew_text_dump",
                "quality": "low",
                "review_published": "20211002",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
            "misc-ageve": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "review_published": "20241111",
            },
        },
    },
    "Revel M22": {
        "brand": "Revel",
        "model": "M22",
        "type": "passive",
        "price": "2000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-m22-speaker-review.12279/",
                "review_published": "20200328",
            },
        },
    },
    "Revel M55XC": {
        "brand": "Revel",
        "model": "M55XC",
        "type": "passive",
        "price": "420",
        "shape": "outdoor",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-m55xc-outdoor-speaker-review.14881/",
                "review_published": "20200723",
            },
        },
    },
    "Revel M80XC": {
        "brand": "Revel",
        "model": "M80XC",
        "type": "passive",
        "price": "900",
        "shape": "outdoor",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-m80xc-review-outdoor-speaker.26878/",
                "review_published": "20210926",
            },
        },
    },
    "Revel W126Be": {
        "brand": "Revel",
        "model": "W126Be",
        "type": "passive",
        "price": "1650",
        "shape": "inwall",
        "amount": "each",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://www.avsforum.com/threads/revel-owners-thread.710918/page-1326#replies",
                "review_published": "20240526",
                "specifications": {
                    "sensitivity": 89,
                    "impedance": 4,
                    "SPL": {
                        "peak": 105,
                    },
                    "size": {
                        "height": 395,
                        "width": 260,
                        "depth": 97,
                    },
                    "weight": 6.4,
                },
            },
        },
    },
    "Revel W226Be": {
        "brand": "Revel",
        "model": "W226Be",
        "type": "passive",
        "price": "2250",
        "shape": "inwall",
        "amount": "each",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://www.avsforum.com/threads/revel-owners-thread.710918/page-1326#replies",
                "review_published": "20240526",
                "specifications": {
                    "sensitivity": 90,
                    "impedance": 4,
                    "SPL": {
                        "peak": 110,
                    },
                    "size": {
                        "height": 582,
                        "width": 260,
                        "depth": 97,
                    },
                    "weight": 7.1,
                },
            },
        },
    },
    "Revel W228Be": {
        "brand": "Revel",
        "model": "W228Be",
        "type": "passive",
        "price": "3500",
        "shape": "inwall",
        "amount": "each",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
                "quality": "medium",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/revel-w228be-in-wall-speaker-review.54848/",
                    "avs": "https://www.avsforum.com/threads/revel-owners-thread.710918/page-1326#replies",
                },
                "review_published": "20240526",
                "specifications": {
                    "sensitivity": 90,
                    "impedance": 4,
                    "SPL": {
                        "peak": 115,
                    },
                    "size": {
                        "height": 938.6,
                        "width": 352.9,
                        "depth": 104.5,
                    },
                    "weight": 14.3,
                },
            },
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/revel-w228be-in-wall-speaker-review.54848/",
                    "avs": "https://www.avsforum.com/threads/revel-owners-thread.710918/page-1326#replies",
                },
                "review_published": "20240602",
            },
        },
    },
    "Revel W553L": {
        "brand": "Revel",
        "model": "W553L",
        "type": "passive",
        "shape": "inwall",
        "price": "495",
        "amount": "each",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/revel_w553l/",
                    "yt": "https://www.youtube.com/watch?v=dPCZJmivufs",
                },
                "review_published": "20220514",
            },
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/revel-w553l-measurements-in-wall-speaker.32072/",
                    "yt": "https://youtu.be/6lK55MF5MMA",
                },
                "review_published": "20220323",
            },
            "vendor": {
                "origin": "Vendors-Revel",
                "format": "webplotdigitizer",
            },
        },
    },
    "Revel W893": {
        "brand": "Revel",
        "model": "W893",
        "type": "passive",
        "shape": "inwall",
        "price": "1100",
        "amount": "each",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/revel_w893/",
                "review_published": "20220514",
            },
        },
    },
    "Revel W990": {
        "brand": "Revel",
        "model": "W990",
        "type": "passive",
        "price": "3500",
        "shape": "inwall",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/revel-w990-review-in-wall-speaker.25954/",
                "review_published": "20210821",
            },
        },
    },
    "Revival Audio Atalante 5": {
        "brand": "Revival Audio",
        "model": "Atalante 5",
        "type": "passive",
        "price": "1100",
        "amount": "each",
        "shape": "floorstanders",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/revival_atalante_5/",
                    "yt": "https://youtu.be/uo9yBHfLDDE?si=mmMrGA3BmPMxbJ6T",
                },
                "review_published": "20240727",
                "specifications": {
                    "sensitivity": 89,
                    "impedance": 4,
                    "size": {
                        "height": 710,
                        "width": 420,
                        "depth": 355,
                    },
                    "weight": 33.0,
                },
            },
        },
    },
    "Rockville SPG88": {
        "brand": "Rockville",
        "model": "SPG88",
        "type": "active",
        "price": "130",
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
    "Rogers LS3|5A": {
        "brand": "Rogers",
        "model": "LS3|5A",
        "type": "passive",
        "price": "3500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/rogers-ls3-5a-bbc-speaker-review.49746/page-2",
                    "bbc": "https://downloads.bbc.co.uk/rd/pubs/reports/1976-29.pdf",
                    "msc": "https://www.facebook.com/Akoustia/posts/195118823028401?ref=embed_post",
                    "str": "https://www.stereophile.com/content/bbc-ls35a-loudspeaker-1989-rogers-version",
                    "tas": "https://www.theabsolutesound.com/articles/2022-golden-ear-rogers-ls3-5a-classic-15-ohm-special-edition-loudspeaker/",
                },
                "review_published": "20231123",
                "specifications": {
                    "sensitivity": 82.5,
                    "impedance": 15,
                    "size": {
                        "height": 305,
                        "width": 190,
                        "depth": 165,
                    },
                    "weight": 4.9,
                },
            },
        },
    },
    "Role Audio Skiff": {
        "brand": "Role Audio",
        "model": "Skiff",
        "type": "passive",
        "price": "400",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/role-audio-skiff-speaker-review.47981/",
                "review_published": "20230918",
            },
        },
    },
    "RSL Outsider II": {
        "brand": "RSL",
        "model": "Outsider II",
        "type": "passive",
        "price": "300",
        "shape": "outdoor",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/rsl-outsider-ii-outdoor-speaker-review.16659/",
                "review_published": "20201011",
            },
        },
    },
    "RSL CG25 Center": {
        "brand": "RSL",
        "model": "CG25 Center",
        "type": "passive",
        "price": "425",
        "shape": "center",
        "amount": "each",
        "default_measurement": "asr-horizontal",
        "measurements": {
            "asr-horizontal": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/rsl-cg25-center-speaker-review.42495/",
                    "adh": "https://www.audioholics.com/bookshelf-speaker-reviews/rsl-cg5-and-cg25",
                    "htr": "https://hometheaterreview.com/rsl-cg5-bookshelf-and-cg25-monitorcenter-channel-reviewed/",
                },
                "review_published": "20230302",
                "specifications": {
                    "sensitivity": 88,
                    "size": {
                        "height": 482,
                        "width": 141,
                        "depth": 247,
                    },
                    "weight": 10.4,
                },
            },
            "asr-vertical": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/rsl-cg25-center-speaker-review.42495/",
                    "adh": "https://www.audioholics.com/bookshelf-speaker-reviews/rsl-cg5-and-cg25",
                    "htr": "https://hometheaterreview.com/rsl-cg5-bookshelf-and-cg25-monitorcenter-channel-reviewed/",
                },
                "review_published": "20230302",
                "specifications": {
                    "sensitivity": 88,
                    "size": {
                        "height": 482,
                        "width": 141,
                        "depth": 247,
                    },
                    "weight": 10.4,
                },
            },
            "misc-audioholics": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://www.audioholics.com/bookshelf-speaker-reviews/rsl-cg5-and-cg25/conclusion",
            },
        },
    },
    "RSL CG5": {
        "brand": "RSL",
        "model": "CG5",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "misc-audioholics",
        "measurements": {
            "misc-audioholics": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://www.audioholics.com/bookshelf-speaker-reviews/rsl-cg5-and-cg25/conclusion",
            },
        },
    },
}
