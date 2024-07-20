from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_e: SpeakerDatabase = {
    "EAW MKC50": {
        "brand": "EAW",
        "model": "MKC50",
        "type": "passive",
        "price": "660",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230325",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 110,
                        "vertical": 110,
                    },
                    "sensitivity": 87,
                    "impedance": 6,
                    "SPL": {
                        "continuous": 115,
                        "peak": 121,
                    },
                    "size": {
                        "height": 235,
                        "width": 165,
                        "depth": 141,
                    },
                    "weight": 3.3,
                },
            },
        },
    },
    "EAW MKC60": {
        "brand": "EAW",
        "model": "MKC60",
        "type": "passive",
        "price": "1200",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230325",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 110,
                        "vertical": 110,
                    },
                    "sensitivity": 89,
                    "impedance": 6,
                    "SPL": {
                        "continuous": 119,
                        "peak": 125,
                    },
                    "size": {
                        "height": 324,
                        "width": 208,
                        "depth": 206,
                    },
                    "weight": 4.9,
                },
            },
        },
    },
    "EAW MKC80": {
        "brand": "EAW",
        "model": "MKC80",
        "type": "passive",
        "price": "1800",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230325",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 60,
                    },
                    "sensitivity": 93,
                    "impedance": 7,
                    "SPL": {
                        "continuous": 126,
                        "peak": 132,
                    },
                    "size": {
                        "height": 422,
                        "width": 255,
                        "depth": 267,
                    },
                    "weight": 10.0,
                },
            },
        },
    },
    "EAW MKC120": {
        "brand": "EAW",
        "model": "MKC120",
        "type": "passive",
        "price": "3000",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230325",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 60,
                    },
                    "sensitivity": 95,
                    "impedance": 7.4,
                    "SPL": {
                        "continuous": 129,
                        "peak": 135,
                    },
                    "size": {
                        "height": 569,
                        "width": 367,
                        "depth": 341,
                    },
                    "weight": 16.8,
                },
            },
        },
    },
    "EAW MKD1000": {
        "brand": "EAW",
        "model": "MKD1000",
        "type": "passive",
        "price": "2900",
        "shape": "liveportable",
        "amount": "each",
        "default_measurement": "vendor-pattern-120x60",
        "measurements": {
            "vendor-pattern-120x60": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 120,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 135,
                    },
                    "size": {
                        "height": 680,
                        "width": 370,
                        "depth": 420,
                    },
                    "weight": 27.3,
                },
            },
            "vendor-pattern-90x60": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 136,
                    },
                    "size": {
                        "height": 680,
                        "width": 370,
                        "depth": 420,
                    },
                    "weight": 27.3,
                },
            },
            "vendor-pattern-60x45": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 45,
                    },
                    "SPL": {
                        "peak": 138,
                    },
                    "size": {
                        "height": 680,
                        "width": 370,
                        "depth": 420,
                    },
                    "weight": 27.3,
                },
            },
        },
    },
    "EAW MKD1200": {
        "brand": "EAW",
        "model": "MKD1200",
        "type": "passive",
        "price": "5000",
        "shape": "liveportable",
        "amount": "each",
        "default_measurement": "vendor-pattern-90x45",
        "measurements": {
            "vendor-pattern-90x45": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 45,
                    },
                    "SPL": {
                        "peak": 139,
                    },
                    "size": {
                        "height": 680,
                        "width": 370,
                        "depth": 420,
                    },
                    "weight": 47.2,
                },
            },
            "vendor-pattern-60x45": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 45,
                    },
                    "SPL": {
                        "peak": 141,
                    },
                    "size": {
                        "height": 680,
                        "width": 370,
                        "depth": 420,
                    },
                    "weight": 27.3,
                },
            },
        },
    },
    "EAW QX300": {
        "brand": "EAW",
        "model": "QX300",
        "type": "passive",
        "price": "3500",
        "shape": "toursound",
        "amount": "pair",
        "default_measurement": "vendor-pattern-120x60",
        "measurements": {
            "vendor-pattern-120x60": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 120,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 141,
                    },
                    "size": {
                        "height": 602,
                        "width": 602,
                        "depth": 505,
                    },
                    "weight": 43,
                },
            },
            "vendor-pattern-60x45": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 45,
                    },
                    "SPL": {
                        "peak": 145,
                    },
                    "size": {
                        "height": 602,
                        "width": 602,
                        "depth": 505,
                    },
                    "weight": 43,
                },
            },
            "vendor-pattern-60x60": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 144,
                    },
                    "size": {
                        "height": 602,
                        "width": 602,
                        "depth": 505,
                    },
                    "weight": 43,
                },
            },
            #            "vendor-pattern-90x45": {
            #                "origin": "Vendors-EAW",
            #                "format": "gll_hv_txt",
            #                "review_published": "20230326",
            #                "data_acquisition": gll_data_acquisition_std,
            #                "quality": "low",
            #                "specifications": {
            #                    "dispersion": {
            #                        "horizontal": 90,
            #                        "vertical": 45,
            #                    },
            #                    "SPL": {
            #                        "peak": 143,
            #                    },
            #                    "size": {
            #                        "height": 602,
            #                        "width": 602,
            #                        "depth": 505,
            #                    },
            #                    "weight": 43,
            #                },
            #            },
            "vendor-pattern-90x60": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 60,
                    },
                    "SPL": {
                        "peak": 142,
                    },
                    "size": {
                        "height": 602,
                        "width": 602,
                        "depth": 505,
                    },
                    "weight": 43,
                },
            },
            "vendor-pattern-90x90": {
                "origin": "Vendors-EAW",
                "format": "gll_hv_txt",
                "review_published": "20230326",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "SPL": {
                        "peak": 141,
                    },
                    "size": {
                        "height": 602,
                        "width": 602,
                        "depth": 505,
                    },
                    "weight": 43,
                },
            },
        },
    },
    "Edifier Airpulse A100": {
        "brand": "Edifier",
        "model": "Airpulse A100",
        "type": "active",
        "price": "900",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/airpulse-a100-review-powered-speaker.27425/",
                "review_published": "20211019",
            },
        },
    },
    "Edifier MR4": {
        "brand": "Edifier",
        "model": "MR4",
        "type": "active",
        "price": "130",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/edifier-mr4-review-budget-monitor.29068/",
                "review_published": "20211216",
            },
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/edifier_mr4/",
                "review_published": "20220111",
            },
            "misc-audiolabinsight": {
                "origin": "Misc",
                "format": "klippel",
                "quality": "high",
                "review": "https://audiolabinsight.com/t/britz-br-monitor4/246",
                "review_published": "20240720",
            },
        },
    },
    "Edifier R1280T": {
        "brand": "Edifier",
        "model": "R1280T",
        "type": "active",
        "price": "100",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/edifier-r1280t-powered-speaker-review.16112/",
                "review_published": "20200920",
            },
        },
    },
    "Edifier S2000 Mk III": {
        "brand": "Edifier",
        "model": "S2000 Mk III",
        "type": "active",
        "price": "400",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "misc-archimago",
        "measurements": {
            "misc-archimago": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "review": "https://archimago.blogspot.com/2020/10/qspins-audioengine-a2-edifier-s2000-mk.html",
                "quality": "low",
            },
        },
    },
    "Edifier S2000 Pro": {
        "brand": "Edifier",
        "model": "S2000 Pro",
        "type": "active",
        "price": "400",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/edifier-s2000-pro-review-powered-monitor.24255/",
                "review_published": "20210616",
            },
        },
    },
    "Elac Adante AS-61": {
        "brand": "Elac",
        "model": "Adante AS-61",
        "type": "passive",
        "price": "1500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/elac-adante-as-61-speaker-review.11507/#post-329527",
            },
        },
    },
    "Elac BS 314": {
        "brand": "Elac",
        "model": "BS 314",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
        "default_measurement": "misc-nuyes-sealed",
        "measurements": {
            "misc-nuyes-sealed": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "dci": "",
                },
                "notes": "Data gated at 5ms so valid above 200Hz/300Hz and smoothed 1/24th of octave. Sealed measurement",
                "review_published": "20220925",
            },
            "misc-nuyes-ported": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "dci": "",
                },
                "notes": "Data gated at 5ms so valid above 200Hz/300Hz and smoothed 1/24th of octave. Ported measurement",
                "review_published": "20220925",
            },
        },
    },
    "Elac Debut Reference DBR-62": {
        "brand": "Elac",
        "model": "Debut Reference DBR-62",
        "type": "passive",
        "price": "600",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/elac_dbr62/",
                    "yt": "https://youtu.be/VCY_CDu5Xas",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/elac-debut-reference-dbr-62-speaker-review.12232/#post-357719",
                },
                "review_published": "20231221",
                "specifications": {
                    "sensitivity": 86,
                    "impedance": 6,
                    "size": {
                        "height": 275,
                        "width": 207,
                        "depth": 363,
                    },
                    "weight": 8.2,
                },
            },
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/elac-debut-reference-dbr-62-speaker-review.12232/#post-357719",
                "review_published": "20200325",
            },
        },
    },
    "Elac Debut 2.0 B6.2": {
        "brand": "Elac",
        "model": "Debut 2.0 B6.2",
        "type": "passive",
        "price": "245",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/elac-debut-2-0-b6-2-speaker-review.14272/",
            },
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/elac_db62/",
                    "yt": "https://youtu.be/FeicGL2UWzw",
                },
                "review_published": "20220813",
            },
        },
    },
    "Elac Debut 2.0 B5.2": {
        "brand": "Elac",
        "model": "Debut 2.0 B5.2",
        "type": "passive",
        "price": "430",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/elac_db52/",
                "review_published": "20221116",
            },
            "misc-nuyes": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "dci": "https://gall.dcinside.com/mgallery/board/view/?id=speakers&no=265694",
                },
                "notes": "Data gated at 5ms so valid above 200Hz/300Hz and smoothed 1/24th of octave",
                "review_published": "20220901",
            },
        },
    },
    "Elac Debut 2.0 A4.2": {
        "brand": "Elac",
        "model": "Debut 2.0 A4.2",
        "type": "passive",
        "price": "500",
        "shape": "surround",
        "default_measurement": "misc-archimago",
        "measurements": {
            "misc-archimago": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "review": "https://archimago.blogspot.com/2021/01/measurements-elac-debut-20-a42-atmos.html",
                "quality": "low",
            },
        },
    },
    "Elac BS U5 Slim": {
        "brand": "Elac",
        "model": "BS U5 Slim",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/elac-bs-u5-slim-3-way-coaxial-speaker-review.13735/",
            },
        },
    },
    "Elac Carina BS243.4": {
        "brand": "Elac",
        "model": "Carina BS243.4",
        "type": "passive",
        "price": "1000",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/elac-carina-bs243-4-review-bookshelf-speaker.34398/",
                "review_published": "20220528",
            },
        },
    },
    "Elac Uni-Fi 2.0 UB52": {
        "brand": "Elac",
        "model": "Uni-Fi 2.0 UB52",
        "type": "passive",
        "price": "600",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/elac-uni-fi-2-0-review-bookshelf-speaker.19216/",
            },
        },
    },
    "Elac Uni-Fi 2.0 UC52 Center": {
        "brand": "Elac",
        "model": "Uni-Fi 2.0 UC52 Center",
        "type": "passive",
        "price": "319",
        "shape": "center",
        "amount": "each",
        "default_measurement": "eac-horizontal",
        "measurements": {
            "eac-horizontal": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/elac_uc52/",
                "review_published": "20220111",
            },
            "eac-vertical": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/elac_uc52/",
                "review_published": "20220111",
            },
        },
    },
    "Elac Uni-Fi Reference UBR62": {
        "brand": "Elac",
        "model": "Uni-Fi Reference UBR62",
        "type": "passive",
        "price": "1000",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/elac_ubr62/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/elac-ubr62-speaker-review.24585/",
                },
            },
        },
    },
    "Elac Uni-Fi Reference UCR52": {
        "brand": "Elac",
        "model": "Uni-Fi Reference UCR52",
        "type": "passive",
        "price": "700",
        "shape": "center",
        "amount": "each",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/elac-reference-ucr52-review-center-speaker.27200/",
                "review_published": "20211009",
            },
        },
    },
    "Elac Vela BS 403": {
        "brand": "Elac",
        "model": "Vela BS 403",
        "type": "passive",
        "price": "1150",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/elac_vela_bs_403/",
                    "yt": "https://youtu.be/Io6gsJK3pSM",
                },
                "review_published": "20240312",
                "specifications": {
                    "sensitivity": 86,
                    "impedance": 4,
                    "size": {
                        "height": 362,
                        "width": 191,
                        "depth": 240,
                    },
                    "weight": 7.1,
                },
            },
        },
    },
    "Emotiva Airmotiv 6s": {
        "brand": "Emotiva",
        "model": "Airmotiv 6s",
        "type": "active",
        "price": "600",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/emotiva-airmotiv-6s-powered-speaker-review.11185/",
            },
        },
    },
    "Emotiva Airmotiv B1+": {
        "brand": "Emotiva",
        "model": "Airmotiv B1+",
        "type": "passive",
        "price": "300",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/emotiva-airmotiv-b1-review-bookshelf-speaker.22366/",
            },
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/emotiva_airmotiv_b1plus/",
                    "yt": "https://youtu.be/YmKpCb3d7Vk",
                },
            },
            "misc-archimago": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "review": "https://archimago.blogspot.com/2021/02/measurements-emotiva-airmotiv-b1.html",
                "quality": "low",
            },
        },
    },
    "Emotiva Airmotiv B2+": {
        "brand": "Emotiva",
        "model": "Airmotiv B2+",
        "type": "passive",
        "price": "450",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/emotiva_airmotiv_b2plus/",
                },
                "review_published": "20220806",
            },
        },
    },
    "Emotiva Airmotiv C2+": {
        "brand": "Emotiva",
        "model": "Airmotiv C2+",
        "type": "passive",
        "price": "399",
        "shape": "center",
        "amount": "each",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/emotiva_airmotiv_c2plus/",
                    "yt": "",
                },
                "review_published": "20211212",
            },
        },
    },
    "Emotiva Airmotiv C1+": {
        "brand": "Emotiva",
        "model": "Airmotiv C1+",
        "type": "passive",
        "price": "300",
        "shape": "center",
        "amount": "each",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/emotiva_airmotiv_c1plus/",
                    "yt": "",
                },
                "review_published": "20220217",
            },
        },
    },
    "Emotiva Airmotiv T2+": {
        "brand": "Emotiva",
        "model": "Airmotiv T2+",
        "type": "passive",
        "price": "999",
        "shape": "floorstanders",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/emotiva_airmotiv_t2plus/",
                    "yt": "https://www.youtube.com/watch?v=ulFplRqEd2U",
                },
                "review_published": "20211122",
            },
        },
    },
    "Endow Audio Bravura 7": {
        "brand": "Endow Audio",
        "model": "Bravura 7",
        "type": "passive",
        "price": "6500",
        "shape": "omnidirectional",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/endow_bravura_7/",
                    "yt": "https://youtu.be/tPW8Y4f4sPs",
                },
                "review_published": "20221116",
            },
        },
    },
    "Epos ES14N": {
        "brand": "Epos",
        "model": "ES14N",
        "type": "passive",
        "price": "2000",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "high",
                "reviews": {
                    "ref": "https://karl-heinz-fink.de/the-measurements-checking-out-the-epos-14n",
                    "whf": "https://www.whathifi.com/reviews/epos-es14n",
                    "ahl": "https://www.audioholics.com/bookshelf-speaker-reviews/epos-es14n",
                    "avf": "https://www.avforums.com/reviews/epos-es14n-standmount-speaker-review.20944/",
                },
                "review_published": "20230926",
                "specifications": {
                    "sensitivity": 87,
                    "impedance": 4.3,
                    "size": {
                        "height": 491,
                        "width": 250,
                        "depth": 385,
                    },
                    "weight": 16,
                },
                "notes": "data is Klippel generated, voltage is 2.83V and results are smoothed at 1/12 octave which may increase the score a bit",
            },
        },
    },
    "Essence Electrostatic Model 1600": {
        "brand": "Essence Electrostatic",
        "model": "Model 1600",
        "type": "passive",
        "price": "",
        "shape": "panel",
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
    "EV EVID-S4.2": {
        "brand": "EV",
        "model": "EVID-S4.2",
        "type": "passive",
        "price": "240",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230117",
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 110,
                        "vertical": 110,
                    },
                    "sensitivity": 87,
                    "impedance": 6,
                    "SPL": {
                        "continuous": 103,
                        "peak": 109,
                    },
                    "size": {
                        "height": 193,
                        "width": 140,
                        "depth": 118,
                    },
                    "weight": 1.5,
                },
            },
        },
    },
    "EV EVID-S5.2": {
        "brand": "EV",
        "model": "EVID-S5.2",
        "type": "passive",
        "price": "390",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "quality": "medium",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230117",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "sensitivity": 90,
                    "impedance": 6,
                    "SPL": {
                        "continuous": 103,
                        "peak": 109,
                    },
                    "size": {
                        "height": 255,
                        "width": 180,
                        "depth": 151,
                    },
                    "weight": 2.7,
                },
            },
        },
    },
    "EV EVID-S5.2X": {
        "brand": "EV",
        "model": "EVID-S5.2X",
        "type": "passive",
        "price": "420",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230117",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "sensitivity": 90,
                    "impedance": 6,
                    "SPL": {
                        "continuous": 109,
                        "peak": 115,
                    },
                    "size": {
                        "height": 255,
                        "width": 180,
                        "depth": 151,
                    },
                    "weight": 2.7,
                },
            },
        },
    },
    "EV EVID-S8.2": {
        "brand": "EV",
        "model": "EVID-S8.2",
        "type": "passive",
        "price": "560",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230117",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "sensitivity": 90,
                    "impedance": 6,
                    "SPL": {
                        "continuous": 110,
                        "peak": 116,
                    },
                    "size": {
                        "height": 390,
                        "width": 223,
                        "depth": 151,
                    },
                    "weight": 5.1,
                },
            },
        },
    },
    "EV EVC-1082": {
        "brand": "EV",
        "model": "EVC-1082",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230117",
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 60,
                    },
                    "sensitivity": 91,
                    "impedance": 6,
                    "SPL": {
                        "peak": 120,
                    },
                    "size": {
                        "height": 492,
                        "width": 248,
                        "depth": 277,
                    },
                    "weight": 11.2,
                },
            },
        },
    },
    "EV EVC-1122": {
        "brand": "EV",
        "model": "EVC-1122",
        "type": "passive",
        "price": "1400",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x55",
        "measurements": {
            "vendor-pattern-90x55": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230118",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 55,
                    },
                    "sensitivity": 95,
                    "impedance": 7,
                    "SPL": {
                        "peak": 126,
                    },
                    "size": {
                        "height": 616,
                        "width": 395,
                        "depth": 401,
                    },
                    "weight": 20.3,
                },
            },
        },
    },
    "EV EVC-1152": {
        "brand": "EV",
        "model": "EVC-1152",
        "type": "passive",
        "price": "1500",
        "amount": "each",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-90x55",
        "measurements": {
            "vendor-pattern-90x55": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230118",
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 55,
                    },
                    "sensitivity": 98,
                    "impedance": 7,
                    "SPL": {
                        "peak": 129,
                    },
                    "size": {
                        "height": 684,
                        "width": 433,
                        "depth": 451,
                    },
                    "weight": 27.7,
                },
            },
        },
    },
    "EV MFX-12MC": {
        "brand": "EV",
        "model": "MFX-12MC",
        "type": "active",
        "price": "6000",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-60x40",
        "measurements": {
            "vendor-pattern-60x40": {  # FOH FR Biamp
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230115",
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 40,
                    },
                    "sensitivity": 97,
                    "impedance": 8,
                    "SPL": {
                        "peak": 135,
                    },
                    "size": {
                        "height": 500,
                        "width": 420,
                        "depth": 298,
                    },
                    "weight": 19,
                },
            },
            "vendor-pattern-40x60": {  # MON FR Biamp
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230115",
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 40,
                        "vertical": 60,
                    },
                    "sensitivity": 97,
                    "impedance": 8,
                    "SPL": {
                        "peak": 135,
                    },
                    "size": {
                        "height": 500,
                        "width": 420,
                        "depth": 298,
                    },
                    "weight": 19,
                },
            },
        },
    },
    "EV MFX-15MC": {
        "brand": "EV",
        "model": "MFX-15MC",
        "type": "active",
        "price": "6000",
        "amount": "pair",
        "shape": "liveportable",
        "default_measurement": "vendor-pattern-60x40",
        "measurements": {
            "vendor-pattern-60x40": {  # FOH FR BiAmp
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230115",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 40,
                    },
                    "sensitivity": 97,
                    "impedance": 8,
                    "SPL": {
                        "peak": 135,
                    },
                    "size": {
                        "height": 600,
                        "width": 500,
                        "depth": 339,
                    },
                    "weight": 23,
                },
            },
            "vendor-pattern-40x60": {  # MON FR BiAmp
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230115",
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 40,
                        "vertical": 60,
                    },
                    "sensitivity": 97,
                    "impedance": 8,
                    "SPL": {
                        "peak": 135,
                    },
                    "size": {
                        "height": 600,
                        "width": 500,
                        "depth": 339,
                    },
                    "weight": 23,
                },
            },
        },
    },
    "EV MTS-4153": {
        "brand": "EV",
        "model": "MTS-4153",
        "type": "active",
        "price": "",
        "amount": "pair",
        "shape": "toursound",
        "default_measurement": "vendor-pattern-60x40",
        "measurements": {
            "vendor-pattern-60x40": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "quality": "medium",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230118",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 40,
                    },
                    "impedance": 6,
                    "SPL": {
                        "peak": 151,
                    },
                    "size": {
                        "height": 1092,
                        "width": 1092,
                        "depth": 1096,
                    },
                    "weight": 160,
                },
            },
            "vendor-pattern-40x30": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230118",
                "specifications": {
                    "dispersion": {
                        "horizontal": 40,
                        "vertical": 30,
                    },
                    "impedance": 6,
                    "SPL": {
                        "peak": 151,
                    },
                    "size": {
                        "height": 1092,
                        "width": 1092,
                        "depth": 1491,
                    },
                    "weight": 196,
                },
            },
        },
    },
    "EV MTS-6154": {
        "brand": "EV",
        "model": "MTS-6154",
        "type": "active",
        "price": "",
        "amount": "pair",
        "shape": "toursound",
        "default_measurement": "vendor-pattern-60x40",
        "measurements": {
            "vendor-pattern-60x40": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20230118",
                "specifications": {
                    "dispersion": {
                        "horizontal": 60,
                        "vertical": 40,
                    },
                    "impedance": 6,
                    "SPL": {
                        "peak": 151,
                    },
                    "size": {
                        "height": 1092,
                        "width": 1092,
                        "depth": 1096,
                    },
                    "weight": 160,
                },
            },
            "vendor-pattern-40x30": {
                "origin": "Vendors-EV",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20230118",
                "quality": "medium",
                "specifications": {
                    "dispersion": {
                        "horizontal": 40,
                        "vertical": 30,
                    },
                    "impedance": 6,
                    "SPL": {
                        "peak": 151,
                    },
                    "size": {
                        "height": 1092,
                        "width": 1092,
                        "depth": 1494,
                    },
                    "weight": 213,
                },
            },
        },
    },
    "Eve Audio SC305": {
        "brand": "Eve Audio",
        "model": "SC305",
        "type": "active",
        "price": "655",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/eve-audio-sc305-studio-monitor-review.37752/",
                "review_published": "20220924",
            },
        },
    },
    "Ex-Machina Pulsar MKII": {
        "brand": "Ex-Machina",
        "model": "Pulsar MKII",
        "type": "active",
        "price": "11700",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/ex_machina_pulsar_mkii/",
                },
                "specifications": {
                    "SPL": {
                        "peak": 110,
                    },
                    "size": {
                        "height": 483,
                        "width": 289,
                        "depth": 345,
                    },
                    "weight": 23,
                },
                "review_published": "20230312",
            },
        },
    },
}
