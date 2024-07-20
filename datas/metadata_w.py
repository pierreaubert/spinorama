# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_w: SpeakerDatabase = {
    "Wharfedale Aura 2": {
        "brand": "Wharfedale",
        "model": "Aura 2",
        "type": "passive",
        "price": "2500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/wharfedale_aura_2",
                    "yt": "https://youtu.be/MCNQDNpM4x0?si=ROqUZUaKHrFvY4XH",
                },
                "review_published": "20240112",
                "specifications": {
                    "sensitivity": 88,
                    "impedance": 6,
                    "SPL": {
                        "peak": 103,
                    },
                    "size": {
                        "height": 560,
                        "width": 286,
                        "depth": 352,
                    },
                    "weight": 20.5,
                },
            },
        },
    },
    "Wharfedale EVO 4.1": {
        "brand": "Wharfedale",
        "model": "EVO 4.1",
        "type": "passive",
        "price": "800",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/wharfedale-evo-4-1-review-speaker.28305/",
                "review_published": "20211121",
            },
        },
    },
    "Wharfedale Diamond 12.1": {
        "brand": "Wharfedale",
        "model": "Diamond 12.1",
        "type": "passive",
        "price": "800",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/wharfedale-diamond-12-1-review-speaker.26780/",
                "review_published": "20210922",
            },
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/wharfedale_12_1/",
                "review_published": "20220814",
            },
        },
    },
    "Wharfedale Diamond 220": {
        "brand": "Wharfedale",
        "model": "Diamond 220",
        "type": "passive",
        "price": "200",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/wharfedale-diamond-220-budget-speaker-review.16752/",
                "review_published": "20201014",
            },
        },
    },
    "Wharfedale Denton 80th Anniversary": {
        "brand": "Wharfedale",
        "model": "Denton 80th Anniversary",
        "type": "passive",
        "price": "600",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/wharfedale-denton-80th-anniversary-speaker-review.51847/",
                "review_published": "20240130",
            },
        },
    },
    "Wharfedale Linton 85th Anniversary": {
        "brand": "Wharfedale",
        "model": "Linton 85th Anniversary",
        "type": "passive",
        "price": "1000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/wharfedale_linton_85/",
                    "yt": "https://youtu.be/CaxknyOrf3I",
                    "tnr": "https://topnewreview.com/wharfedale-linton-85th-anniversary-review/#measured-performance",
                    "tas": "https://www.theabsolutesound.com/articles/wharfedale-linton-85th-anniversary-loudspeaker",
                    "whf": "https://www.whathifi.com/reviews/wharfedale-linton",
                },
                "review_published": "20220704",
            },
        },
    },
    "Wharfedale Pro Delta X10": {
        "brand": "Wharfedale Pro",
        "model": "Delta X10",
        "type": "passive",
        "price": "640",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-Wharfedale Pro",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20221026",
                "quality": "low",
            },
        },
    },
    "Wharfedale Super Denton": {
        "skip": True,
        "brand": "Wharfedale",
        "model": "Super Denton",
        "type": "passive",
        "price": "1400",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/wharfedale_super_denton/",
                    "yt": "https://youtu.be/5Xb9Ku0Fy_E",
                },
                "review_published": "202404xx",
                "specifications": {
                    "sensitivity": 87,
                    "impedance": 3.4,
                    "SPL": {
                        "peak": 103,
                    },
                    "size": {
                        "height": 360,
                        "width": 246,
                        "depth": 295,
                    },
                    "weight": 9.2,
                },
            },
        },
    },
    "Wilson Audio TuneTot": {
        "brand": "Wilson Audio",
        "model": "TuneTot",
        "type": "passive",
        "price": "10000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/wilson-audio-tunetot-review-high-end-bookshelf-speaker.29219/",
                "review_published": "20211221",
            },
        },
    },
}
