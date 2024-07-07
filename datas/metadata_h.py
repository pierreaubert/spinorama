from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_h: SpeakerDatabase = {
    "Harbeth Monitor 30.0": {
        "brand": "Harbeth",
        "model": "Monitor 30.0",
        "type": "passive",
        "price": "3200",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/harbeth-monitor-30-speaker-review.11108/",
            },
        },
    },
    "Hedd Type 20 MK2": {
        "brand": "Hedd",
        "model": "Type 20 MK2",
        "type": "active",
        "price": "2400",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "asr-ported",
        "measurements": {
            "asr-ported": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/hedd-type-20-mk2-monitor-review.41455/",
                "review_published": "20230129",
            },
            "asr-sealed": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/hedd-type-20-mk2-monitor-review.41455/",
                "review_published": "20230129",
            },
        },
    },
    "Hivi 3.1A DIY": {
        "brand": "Hivi",
        "model": "3.1A DIY",
        "type": "passive",
        "price": "300",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/hivi-3-1a-diy-speaker-with-sehlin-mod-review.15802/",
            },
        },
    },
    "Hivi Swan X3": {
        "brand": "Hivi",
        "model": "Swan X3",
        "type": "active",
        "price": "250",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/swan-hivi-x3-review-active-monitors.35376/",
                "review_published": "20220701",
            },
        },
    },
    "HK Audio LINEAR 5 112 F": {
        "brand": "HK Audio",
        "model": "LINEAR 5 112 F",
        "type": "passive",
        "price": "605",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "reviews": {
                    "sos": "https://www.soundonsound.com/reviews/hk-audio-linear-5-112fa-l-sub-2000a",
                },
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 55,
                    },
                    "sensitivity": 103,
                    "impedance": 8,
                    "SPL": {
                        "continuous": 129,
                        "peak": 135,
                    },
                    "size": {
                        "height": 668,
                        "width": 365,
                        "depth": 370,
                    },
                    "weight": 23.9,
                },
            },
        },
    },
    "HK Audio LINEAR 5 112 FA": {
        "brand": "HK Audio",
        "model": "LINEAR 5 112 FA",
        "type": "active",
        "price": "955",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "reviews": {
                    "sos": "https://www.soundonsound.com/reviews/hk-audio-linear-5-112fa-l-sub-2000a",
                },
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 55,
                    },
                    "SPL": {
                        "continuous": 127,
                        "peak": 135,
                    },
                    "size": {
                        "height": 668,
                        "width": 365,
                        "depth": 370,
                    },
                    "weight": 23.9,
                },
            },
        },
    },
    "HK Audio LINEAR 5 112 X": {
        "brand": "HK Audio",
        "model": "LINEAR 5 112 X",
        "type": "passive",
        "price": "645",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "reviews": {
                    "sos": "https://www.soundonsound.com/reviews/hk-audio-linear-5-112fa-l-sub-2000a",
                },
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 40,
                    },
                    "sensitivity": 98,
                    "impedance": 8,
                    "SPL": {
                        "continuous": 127,
                        "peak": 135,
                    },
                    "size": {
                        "height": 668,
                        "width": 365,
                        "depth": 370,
                    },
                    "weight": 19.5,
                },
            },
        },
    },
    "HK Audio LINEAR 5 112 XA": {
        "brand": "HK Audio",
        "model": "LINEAR 5 112 XA",
        "type": "active",
        "price": "800",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "reviews": {
                    "sos": "https://www.soundonsound.com/reviews/hk-audio-linear-5-112fa-l-sub-2000a",
                },
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 45,
                    },
                    "SPL": {
                        "continuous": 128,
                        "peak": 136,
                    },
                    "size": {
                        "height": 668,
                        "width": 365,
                        "depth": 370,
                    },
                    "weight": 21.1,
                },
            },
        },
    },
    "HK Audio LINEAR 7 110 XA": {
        "brand": "HK Audio",
        "model": "LINEAR 7 110 XA",
        "type": "active",
        "price": "1250",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 80,
                        "vertical": 60,
                    },
                    "SPL": {
                        "continuous": 126,
                        "peak": 129,
                    },
                    "size": {
                        "height": 540,
                        "width": 360,
                        "depth": 310,
                    },
                    "weight": 17,
                },
            },
        },
    },
    "HK Audio LINEAR 7 112 XA": {
        "brand": "HK Audio",
        "model": "LINEAR 7 112 XA",
        "type": "active",
        "price": "1450",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 80,
                        "vertical": 60,
                    },
                    "SPL": {
                        "continuous": 128,
                        "peak": 131,
                    },
                    "size": {
                        "height": 670,
                        "width": 370,
                        "depth": 310,
                    },
                    "weight": 21,
                },
            },
        },
    },
    "HK Audio LINEAR 7 112 FA": {
        "brand": "HK Audio",
        "model": "LINEAR 7 112 FA",
        "type": "active",
        "price": "1450",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 80,
                        "vertical": 60,
                    },
                    "SPL": {
                        "continuous": 128,
                        "peak": 131,
                    },
                    "size": {
                        "height": 670,
                        "width": 370,
                        "depth": 310,
                    },
                    "weight": 21,
                },
            },
        },
    },
    "HK Audio LINEAR 7 115 FA": {
        "brand": "HK Audio",
        "model": "LINEAR 7 115 FA",
        "type": "active",
        "price": "1550",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 40,
                    },
                    "SPL": {
                        "continuous": 129,
                        "peak": 134,
                    },
                    "size": {
                        "height": 710,
                        "width": 450,
                        "depth": 450,
                    },
                    "weight": 32,
                },
            },
        },
    },
    "HK Audio LINEAR 9 110 XA": {
        "brand": "HK Audio",
        "model": "LINEAR 9 110 XA",
        "type": "active",
        "price": "1500",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 80,
                        "vertical": 60,
                    },
                    "SPL": {
                        "continuous": 126,
                        "peak": 129,
                    },
                    "size": {
                        "height": 540,
                        "width": 360,
                        "depth": 310,
                    },
                    "weight": 16.5,
                },
            },
        },
    },
    "HK Audio LINEAR 9 112 XA": {
        "brand": "HK Audio",
        "model": "LINEAR 9 112 XA",
        "type": "active",
        "price": "1600",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-HK Audio",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20230422",
                "specifications": {
                    "dispersion": {
                        "horizontal": 80,
                        "vertical": 60,
                    },
                    "SPL": {
                        "continuous": 128,
                        "peak": 131,
                    },
                    "size": {
                        "height": 670,
                        "width": 370,
                        "depth": 310,
                    },
                    "weight": 20.5,
                },
            },
        },
    },
    "Hsu Research CCB-8": {
        "brand": "Hsu Research",
        "model": "CCB-8",
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
                "review": "https://www.audioholics.com/bookshelf-speaker-reviews/ccb-8-bookshelf/measurements",
            },
        },
    },
    "HTD Level THREE": {
        "brand": "HTD",
        "model": "Level THREE",
        "type": "passive",
        "price": "429",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/htd-level-three-review-bookshelf-speaker.26566/",
                "review_published": "20210912",
            },
        },
    },
    "Hsu Research HB-1 MK2": {
        "brand": "Hsu Research",
        "model": "HB-1 MK2",
        "type": "passive",
        "price": "218",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/hsu-hb-1-mk2-review-horn-speaker.24445/",
            },
        },
    },
    "Human Speakers 81 dk": {
        "brand": "Human Speakers",
        "model": "81 dk",
        "type": "passive",
        "price": "1200",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/human-speakers-81-dk-review.50915/",
                "review_published": "20240104",
            },
        },
    },
}
