# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_t: SpeakerDatabase = {
    "TAD COMPACT REFERENCE ONE CR1TX": {
        "brand": "TAD",
        "model": "COMPACT REFERENCE ONE CR1TX",
        "type": "passive",
        "price": "85000",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/tad_cr1tx/",
                    "yt": "https://youtu.be/WiFAXve_KjE?si=3uBSyFTPK_lTsQgc",
                },
                "review_published": "20240727",
                "specifications": {
                    "sensitivity": 86,
                    "impedance": 4,
                    "size": {
                        "height": 628,
                        "width": 341,
                        "depth": 446,
                    },
                    "weight": 46,
                },
            },
        },
    },
    "TAD Evolution 2": {
        "brand": "TAD",
        "model": "Evolution 2",
        "type": "passive",
        "price": "20000",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/tad-evolution-2-speaker-review.38949/",
                "review_published": "20221108",
            },
        },
    },
    "Tannoy Definition DC6i": {
        "brand": "Tannoy",
        "model": "Definition DC6i",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
        "default_measurement": "princeton",
        "measurements": {
            "princeton": {
                "origin": "Princeton",
                "format": "princeton",
                "symmetry": "coaxial",
                "review": "https://www.princeton.edu/3D3A/Directivity.html",
                "review_published": "20151001",
            },
        },
    },
    "Tannoy Reveal 501a": {
        "brand": "Tannoy",
        "model": "Reveal 501a",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
        "default_measurement": "misc-archimago",
        "measurements": {
            "misc-archimago": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "review": "https://archimago.blogspot.com/2020/12/measurements-tannoy-reveal-501a-powered.html",
                "quality": "low",
            },
        },
    },
    "Tannoy Revolution XT6": {
        "brand": "Tannoy",
        "model": "Revolution XT6",
        "type": "passive",
        "price": "1400",
        "shape": "floorstanders",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/tannoy-revolution-xt-6-speaker-review.14662/",
                "review_published": "20200712",
            },
        },
    },
    "Tannoy System 600": {
        "brand": "Tannoy",
        "model": "System 600",
        "type": "passive",
        "price": "",
        "shape": "cinema",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/tannoy-system-600-speaker-review.11919/",
                "review_published": "20200307",
            },
        },
    },
    "Tannoy VQ100": {
        "brand": "Tannoy",
        "model": "VQ100",
        "type": "passive",
        "price": "2500",
        "amount": "each",
        "shape": "cinema",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Tannoy",
                "format": "gll_hv_txt",
                "quality": "medium",
                "review_published": "20230909",
                "data_acquisition": gll_data_acquisition_std,
                "specifications": {
                    "impedance": 8,
                    "size": {
                        "height": 925,
                        "width": 694,
                        "depth": 515,
                    },
                },
            },
        },
    },
    "Tannoy VX12": {
        "brand": "Tannoy",
        "model": "VX12",
        "type": "passive",
        "price": "860",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "vendor-pattern-75x40",
        "measurements": {
            "vendor-pattern-75x40": {
                "origin": "Vendors-Tannoy",
                "format": "gll_hv_txt",
                "quality": "medium",
                "review_published": "20230909",
                "data_acquisition": gll_data_acquisition_std,
                "specifications": {
                    "dispersion": {
                        "horizontal": 75,
                        "vertical": 40,
                    },
                    "impedance": 8,
                    "size": {
                        "height": 486,
                        "width": 370,
                        "depth": 360,
                    },
                },
            },
        },
    },
    "Teac S-300HR": {
        "brand": "Teac",
        "model": "S-300HR",
        "type": "passive",
        "price": "800",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/teac-s-300hr-review-speaker.26186/",
                "review_published": "20210830",
            },
        },
    },
    "Technics SB-C700": {
        "brand": "Technics",
        "model": "SB-C700",
        "type": "passive",
        "price": "1700",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/technics-sb-c700-review-coaxial-bookshelf.30607/",
                "review_published": "20220206",
            },
        },
    },
    "Technics SB-F1": {
        "brand": "Technics",
        "model": "SB-F1",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/technics-sb-f1-review-vintage-speaker.32975/",
                "review_published": "20220413",
            },
        },
    },
    "Tekton M-Lore": {
        "brand": "Tekton",
        "model": "M-Lore",
        "type": "passive",
        "price": "750",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/tekton-m-lore-speaker-review.48732/",
                "review_published": "20231017",
                "specifications": {
                    "sensitivity": 95,
                    "impedance": 8,
                    "size": {
                        "height": 863,
                        "width": 231,
                        "depth": 254,
                    },
                    "weight": 20,
                },
            },
        },
    },
    "Tekton Troubadour": {
        "brand": "Tekton",
        "model": "Troubadour",
        "type": "passive",
        "price": "1000",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/tekton_troubadour/",
                    "yt": "https://youtu.be/ItAwcW-3Kv4",
                },
                "review_published": "20240414",
                "specifications": {
                    "size": {
                        "height": 533,
                        "width": 533,
                        "depth": 228,
                    },
                    "weight": 14.5,
                },
            },
        },
    },
    "Thomann Swissonic A305": {
        "brand": "Thomann Swissonic",
        "model": "A305",
        "type": "active",
        "price": "220",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/thomann_swissonic_a305/",
                    "yt": "",
                },
                "review_published": "20240112",
                "specifications": {
                    "size": {
                        "height": 298,
                        "width": 185,
                        "depth": 231,
                    },
                    "weight": 4.4,
                },
            },
        },
    },
    "Thomann Swissonic A306": {
        "brand": "Thomann Swissonic",
        "model": "A306",
        "type": "active",
        "price": "250",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/thomann_swissonic_a306/",
                    "yt": "https://youtu.be/SMXj6u8pSjM",
                },
                "review_published": "20231212",
                "specifications": {
                    "size": {
                        "height": 361,
                        "width": 224,
                        "depth": 282,
                    },
                    "weight": 6.17,
                },
                "notes": "Treble was set at -2dB.",
            },
        },
    },
    "Theory Audio SB25": {
        "brand": "Theory Audio",
        "model": "SB25",
        "type": "passive",
        "price": "1700",
        "amout": "each",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/theory-audio-sb25-speaker-system-review.56069/",
                },
                "review_published": "20240731",
                "specifications": {
                    "dispersion": {
                        "horizontal": 120,
                        "vertical": 40,
                    },
                    "sensitivity": 94,
                    "impedance": 4,
                    "SPL": {
                        "peak": 117,
                    },
                    "size": {
                        "height": 546,
                        "width": 243,
                        "depth": 96,
                    },
                    "weight": 11,
                },
            },
            "vendor-pattern-120x40": {
                "origin": "Vendors-Theory Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20230115",
            },
        },
    },
    "Totem Acoustic Kin One": {
        "skip": True,
        "brand": "Totem Acoustic",
        "model": "Kin One",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "",
                    "yt": "https://youtu.be/37Nd7Uz_zlk",
                },
                "review_published": "202404xx",
                "specifications": {
                    "sensitivity": 89,
                    "impedance": 6,
                    "size": {
                        "height": 143,
                        "width": 237,
                        "depth": 159,
                    },
                    "weight": 2.83,
                },
            },
        },
    },
    "Totem Acoustics Rainmaker": {
        "brand": "Totem Acoustics",
        "model": "Rainmaker",
        "type": "passive",
        "price": "500",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/totem-acoustics-rainmaker-speaker-review.40906/",
                "review_published": "20230112",
            },
        },
    },
    "Triad In-Room Gold LCR": {
        "brand": "Triad",
        "model": "In-Room Gold LCR",
        "type": "passive",
        "price": "6600",
        "shape": "cinema",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://erinsaudiocorner.com/loudspeakers/triad_inroom_gold_lcr/",
                    "yt": "https://youtu.be/gNKs0Dj2v5E",
                },
                "review_published": "20230602",
            },
        },
    },
    "Triangle Borea BR03": {
        "brand": "Triangle",
        "model": "Borea BR03",
        "type": "passive",
        "price": "500",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/triangle_br03/",
                    "yt": "https://youtu.be/MNBWQGv2-SM",
                },
                "review_published": "20231220",
                "specifications": {
                    "sensitivity": 90,
                    "impedance": 4.2,
                    "size": {
                        "height": 380,
                        "width": 206,
                        "depth": 314,
                    },
                    "weight": 6.26,
                },
            },
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/triangle-borea-br03-review-bookshelf-speaker.21739/",
                "review_published": "20200325",
            },
        },
    },
    "Triangle Esprit Antal Ez": {
        "brand": "Triangle",
        "model": "Esprit Antal Ez",
        "type": "passive",
        "price": "890",
        "shape": "floorstanders",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/triangle-esprit-antal-ez-review-tower-speaker.22080/",
                "review_published": "20210403",
            },
        },
    },
    "Turbosound NuQ62": {
        "brand": "Turbosound",
        "model": "NuQ62",
        "type": "passive",
        "price": "329",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "sensitivity": 88,
                    "impedance": 16,
                    "SPL": {
                        "peak": 116,
                    },
                    "size": {
                        "height": 350,
                        "width": 190,
                        "depth": 210,
                    },
                    "weight": 6.3,
                },
            },
        },
    },
    "Turbosound NuQ82": {
        "brand": "Turbosound",
        "model": "NuQ82",
        "type": "passive",
        "price": "500",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "sensitivity": 93,
                    "impedance": 8,
                    "SPL": {
                        "peak": 123,
                    },
                    "size": {
                        "height": 464,
                        "width": 274,
                        "depth": 220,
                    },
                    "weight": 10.2,
                },
            },
        },
    },
    "Turbosound NuQ102": {
        "brand": "Turbosound",
        "model": "NuQ102",
        "type": "passive",
        "price": "530",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 60,
                    },
                    "sensitivity": 93,
                    "impedance": 6,
                    "SPL": {
                        "peak": 124,
                    },
                    "size": {
                        "height": 525,
                        "width": 318,
                        "depth": 258,
                    },
                    "weight": 12.7,
                },
            },
        },
    },
    "Turbosound NuQ122": {
        "brand": "Turbosound",
        "model": "NuQ122",
        "type": "passive",
        "price": "800",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
                "specifications": {
                    "dispersion": {
                        "horizontal": 70,
                        "vertical": 70,
                    },
                    "sensitivity": 96,
                    "impedance": 6,
                    "SPL": {
                        "peak": 128,
                    },
                    "size": {
                        "height": 655,
                        "width": 374,
                        "depth": 340,
                    },
                    "weight": 19.6,
                },
            },
        },
    },
    "Turbosound NuQ152": {
        "brand": "Turbosound",
        "model": "NuQ152",
        "type": "passive",
        "price": "950",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
                "specifications": {
                    "dispersion": {
                        "horizontal": 70,
                        "vertical": 70,
                    },
                    "sensitivity": 97,
                    "impedance": 6,
                    "SPL": {
                        "peak": 130,
                    },
                    "size": {
                        "height": 712,
                        "width": 430,
                        "depth": 385,
                    },
                    "weight": 24.4,
                },
            },
        },
    },
    "Turbosound TCS62 V": {
        "brand": "Turbosound",
        "model": "TCS62 V",
        "type": "passive",
        "price": "",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
            },
        },
    },
    "Turbosound TCS122": {
        "brand": "Turbosound",
        "model": "TCS122",
        "type": "passive",
        "price": "",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x40",
        "measurements": {
            "vendor-pattern-90x40": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 40,
                    },
                    "sensitivity": 96,
                    "impedance": 6,
                    "SPL": {
                        "peak": 130,
                    },
                    "size": {
                        "height": 834,
                        "width": 399,
                        "depth": 425,
                    },
                    "weight": 26.5,
                },
            },
        },
    },
    "Turbosound TCS152": {
        "brand": "Turbosound",
        "model": "TCS152",
        "type": "passive",
        "price": "",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x40",
        "measurements": {
            "vendor-pattern-90x40": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 60,
                    },
                    "sensitivity": 97,
                    "impedance": 6,
                    "SPL": {
                        "peak": 131,
                    },
                    "size": {
                        "height": 834,
                        "width": 473,
                        "depth": 451,
                    },
                    "weight": 28.9,
                },
            },
        },
    },
    "Turbosound TBV123": {
        "brand": "Turbosound",
        "model": "TBV123",
        "type": "passive",
        "price": "2600",
        "amount": "each",
        "shape": "toursound",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Turbosound",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20221205",
                "parameters": {
                    "mean_min": 50,
                    "mean_max": 500,
                },
                "specifications": {
                    "dispersion": {
                        "horizontal": 100,
                        "vertical": 15,
                    },
                    "sensitivity": 97,
                    "impedance": 6,
                    "SPL": {
                        "continuous": 125,
                        "peak": 131,
                    },
                    "size": {
                        "height": 344,
                        "width": 598,
                        "depth": 399,
                    },
                    "weight": 22.0,
                },
                "notes": "TODO: add exact config",
            },
        },
    },
}
