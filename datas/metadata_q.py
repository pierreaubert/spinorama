from . import SpeakerDatabase, gll_data_acquisition_std

note_qsc_gll = "Data provided by QSC is of good quality but highly smoothed"

speakers_info_q: SpeakerDatabase = {
    "Q Acoustics 3020i": {
        "brand": "Q Acoustics",
        "model": "3020i",
        "type": "passive",
        "price": "315",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/q-acoustics-3020i-bookshelf-speaker-review.14568/",
                "review_published": "20200706",
            },
        },
    },
    "Q Acoustics 3030i": {
        "brand": "Q Acoustics",
        "model": "3030i",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "misc-napilopez",
        "measurements": {
            "misc-napilopez": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/q-acoustics-3030i-low-spinorama-and-other-measurements.12500/",
                    "tnw": "https://thenextweb.com/news/review-the-q-acoustics-3030i-takes-one-of-my-favorite-budget-speakers-and-adds-bass",
                },
            },
        },
    },
    "Q Acoustics 3050i": {
        "skip": True,
        "brand": "Q Acoustics",
        "model": "3050i",
        "type": "passive",
        "price": "750",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/q_acoustics_3050i/",
                    "yt": "",
                },
                "review_published": "20240312",
                "specifications": {
                    "sensitivity": 91,
                    "impedance": 6,
                    "SPL": {
                        "peak": 122,
                    },
                    "size": {
                        "height": 1020,
                        "width": 310,
                        "depth": 320,
                    },
                    "weight": 17.8,
                },
            },
        },
    },
    "Q Acoustics 5020": {
        "brand": "Q Acoustics",
        "model": "5020",
        "type": "passive",
        "price": "900",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/q_acoustics_5020/",
                    "yt": "https://youtu.be/_lEhxLptP9E",
                },
                "review_published": "20230602",
            },
        },
    },
    "Q Acoustics 5040": {
        "brand": "Q Acoustics",
        "model": "5040",
        "type": "passive",
        "price": "1250",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/q_acoustics_5040/",
                    "yt": "https://youtu.be/-EW8YTVEukQ?si=1QIzKeW_ql88x0H2",
                },
                "review_published": "20240115",
                "specifications": {
                    "sensitivity": 91.5,
                    "impedance": 6,
                    "SPL": {
                        "peak": 122,
                    },
                    "size": {
                        "height": 967,
                        "width": 293,
                        "depth": 361,
                    },
                    "weight": 18,
                },
            },
        },
    },
    "Quad Electroacoustics ESL-57": {
        "brand": "Quad Electroacoustics",
        "model": "ESL-57",
        "type": "passive",
        "shape": "panel",
        "price": "",
        "default_measurement": "princeton",
        "measurements": {
            "princeton": {
                "origin": "Princeton",
                "format": "princeton",
                "symmetry": "horizontal",
                "review": "https://www.princeton.edu/3D3A/Directivity.html",
                "review_published": "20151001",
            },
        },
    },
    "QSC K8.2": {
        "brand": "QSC",
        "model": "K8.2",
        "type": "active",
        "price": "740",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-QSC",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20220918",
                "notes": "{}".format(note_qsc_gll),
            },
        },
    },
    "QSC K10.2": {
        "brand": "QSC",
        "model": "K10.2",
        "type": "active",
        "price": "775",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-QSC",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20220918",
                "notes": "{}".format(note_qsc_gll),
            },
        },
    },
    "QSC K12.2": {
        "brand": "QSC",
        "model": "K12.2",
        "type": "active",
        "price": "870",
        "shape": "liveportable",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-QSC",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "review_published": "20220918",
                "notes": "{}".format(note_qsc_gll),
            },
        },
    },
    "Quested S8R": {
        "brand": "Quested",
        "model": "S8R",
        "type": "active",
        "price": "3000",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "misc-sr",
        "measurements": {
            "misc-sr": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://www.soundandrecording.de/equipment/quested-s8r-2-wege-monitor-im-test/",
                "review_published": "20220314",
            },
        },
    },
    "RBH Sound R-515": {
        "brand": "RBH Sound",
        "model": "R-515",
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
    "RBH Sound SV-61R": {
        "brand": "RBH Sound",
        "model": "SV-61R",
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
                "review": "https://www.audioholics.com/bookshelf-speaker-reviews/sv-61r/measurements",
            },
        },
    },
    "RBH Sound PM-8": {
        "brand": "RBH Sound",
        "model": "PM-8",
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
                "review": "https://www.audioholics.com/bookshelf-speaker-reviews/rbh-pm-8-monitor/conclusion",
            },
        },
    },
}
