# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_v: SpeakerDatabase = {
    "Vanatoo Transparent One Encore": {
        "brand": "Vanatoo",
        "model": "Transparent One Encore",
        "type": "active",
        "price": "600",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/vanatoo-transparent-one-encore-powered-speaker.32421/",
                    "yt": "https://youtu.be/tMOp66XdjNo",
                },
                "review_published": "20220330",
            },
        },
    },
    "Vanatoo Transparent One Encore Plus": {
        "brand": "Vanatoo",
        "model": "Transparent One Encore Plus",
        "type": "active",
        "price": "450",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/vanatoo_one_plus/",
                },
                "review_published": "20231201",
            },
        },
    },
    "Vanatoo Transparent Zero": {
        "brand": "Vanatoo",
        "model": "Transparent Zero",
        "type": "active",
        "price": "350",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/vanatoo-transparent-zero-speaker-review.13717/",
                "review_published": "20200531",
            },
        },
    },
    "Vanatoo Transparent Zero Plus": {
        "brand": "Vanatoo",
        "model": "Transparent Zero Plus",
        "type": "active",
        "price": "450",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/vanatoo_zero_plus/",
                    "yt": "https://youtu.be/jztXlVDCBME",
                },
                "review_published": "20231122",
            },
        },
    },
    "Vandersteen VCC-5": {
        "brand": "Vandersteen",
        "model": "VCC-5",
        "type": "passive",
        "price": "2700",
        "shape": "center",
        "amount": "each",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.audiosciencereview.com/forum/index.php?threads/vandersteen-vcc-5-review-center-speaker.27776/",
                },
                "review_published": "20211103",
            },
        },
    },
    "Vandersteen 2c": {
        "brand": "Vandersteen",
        "model": "2c",
        "type": "passive",
        "price": "1200",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/vandersteen_model_2/",
                    "yt": "https://www.youtube.com/watch?v=ErOR2yP6O_U",
                },
                "review_published": "20211111",
            },
        },
    },
    "Vandersteen VLR": {
        "brand": "Vandersteen",
        "model": "VLR",
        "type": "passive",
        "price": "3800",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.audiosciencereview.com/forum/index.php?threads/vandersteen-vlr-speaker-review.35444/",
                },
                "review_published": "20220704",
            },
        },
    },
    "Verdant Audio Bambusa AL 1": {
        "brand": "Verdant Audio",
        "model": "Bambusa AL 1",
        "type": "passive",
        "price": "3500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/verdant-audio-bambusa-al-1-review.12562/",
                "review_published": "20200413",
            },
        },
    },
    "Verdant Audio Bambusa MG 1": {
        "brand": "Verdant Audio",
        "model": "Bambusa MG 1",
        "type": "passive",
        "price": "5000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/verdant-audio-bambusa-mg-1-speaker-review.12385/",
                "review_published": "20200403",
            },
        },
    },
    "Vue Audiotechnik A-8": {
        "brand": "Vue Audiotechnik",
        "model": "A-8",
        "type": "passive",
        "price": "999",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-70x55",
        "measurements": {
            "vendor-pattern-70x55": {
                "origin": "Vendors-Vue Audiotechnik",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230327",
                "specifications": {
                    "dispersion": {
                        "horizontal": 70,
                        "vertical": 55,
                    },
                    "sensitivity": 93,
                    "impedance": 8,
                    "SPL": {
                        "continuous": 118,
                        "peak": 124,
                    },
                    "size": {
                        "height": 460,
                        "width": 286,
                        "depth": 274,
                    },
                    "weight": 13.1,
                },
            },
        },
    },
    "Vue Audiotechnik A-10": {
        "brand": "Vue Audiotechnik",
        "model": "A-10",
        "type": "passive",
        "price": "1200",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-70x55",
        "measurements": {
            "vendor-pattern-70x55": {
                "origin": "Vendors-Vue Audiotechnik",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230327",
                "specifications": {
                    "dispersion": {
                        "horizontal": 70,
                        "vertical": 55,
                    },
                    "sensitivity": 95,
                    "SPL": {
                        "continuous": 121,
                        "peak": 127,
                    },
                    "size": {
                        "height": 535,
                        "width": 340,
                        "depth": 330,
                    },
                    "weight": 14.3,
                },
            },
        },
    },
    "Vue Audiotechnik A-12": {
        "brand": "Vue Audiotechnik",
        "model": "A-12",
        "type": "passive",
        "price": "2000",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-70x55",
        "measurements": {
            "vendor-pattern-70x55": {
                "origin": "Vendors-Vue Audiotechnik",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230327",
                "specifications": {
                    "dispersion": {
                        "horizontal": 70,
                        "vertical": 55,
                    },
                    "sensitivity": 96,
                    "SPL": {
                        "continuous": 122,
                        "peak": 128,
                    },
                    "size": {
                        "height": 620,
                        "width": 390,
                        "depth": 370,
                    },
                    "weight": 21.0,
                },
            },
        },
    },
    "Vue Audiotechnik A-15": {
        "brand": "Vue Audiotechnik",
        "model": "A-15",
        "type": "passive",
        "price": "2500",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-70x55",
        "measurements": {
            "vendor-pattern-70x55": {
                "origin": "Vendors-Vue Audiotechnik",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230327",
                "specifications": {
                    "dispersion": {
                        "horizontal": 70,
                        "vertical": 55,
                    },
                    "sensitivity": 98,
                    "SPL": {
                        "continuous": 125,
                        "peak": 131,
                    },
                    "size": {
                        "height": 716,
                        "width": 450,
                        "depth": 450,
                    },
                    "weight": 27.0,
                },
            },
        },
    },
    "Vue Audiotechnik H-5": {
        "brand": "Vue Audiotechnik",
        "model": "H-5",
        "type": "active",
        "price": "3195",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-120x40",
        "measurements": {
            "vendor-pattern-120x40": {
                "origin": "Vendors-Vue Audiotechnik",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230327",
                "specifications": {
                    "dispersion": {
                        "horizontal": 120,
                        "vertical": 40,
                    },
                    "sensitivity": 93,
                    "SPL": {
                        "continuous": 114,
                        "peak": 120,
                    },
                    "size": {
                        "height": 189,
                        "width": 458,
                        "depth": 298,
                    },
                    "weight": 12.33,
                },
            },
        },
    },
    "Vue Audiotechnik H-8": {
        "brand": "Vue Audiotechnik",
        "model": "H-8",
        "type": "active",
        "price": "3800",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-100x40",
        "measurements": {
            "vendor-pattern-100x40": {
                "origin": "Vendors-Vue Audiotechnik",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230327",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 40,
                    },
                    "sensitivity": 94,
                    "SPL": {
                        "continuous": 116,
                        "peak": 122,
                    },
                    "size": {
                        "height": 460,
                        "width": 286,
                        "depth": 303,
                    },
                    "weight": 23.22,
                },
            },
        },
    },
    "Vue Audiotechnik H-12": {
        "brand": "Vue Audiotechnik",
        "model": "H-12",
        "type": "active",
        "price": "6000",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-60x40",
        "measurements": {
            "vendor-pattern-60x40": {
                "origin": "Vendors-Vue Audiotechnik",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230327",
                "specifications": {
                    "dispersion": {
                        "horizontal": 120,
                        "vertical": 50,
                    },
                    "sensitivity": 96,
                    "SPL": {
                        "continuous": 120,
                        "peak": 125,
                    },
                    "size": {
                        "height": 610,
                        "width": 368,
                        "depth": 387,
                    },
                    "weight": 35.19,
                },
            },
        },
    },
    "Vue Audiotechnik H-15": {
        "brand": "Vue Audiotechnik",
        "model": "H-15",
        "type": "active",
        "price": "6500",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-60x40",
        "measurements": {
            "vendor-pattern-60x40": {
                "origin": "Vendors-Vue Audiotechnik",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20230327",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 40,
                    },
                    "sensitivity": 97,
                    "SPL": {
                        "continuous": 127,
                        "peak": 136,
                    },
                    "size": {
                        "height": 692,
                        "width": 438,
                        "depth": 457,
                    },
                    "weight": 38.05,
                },
            },
        },
    },
}
