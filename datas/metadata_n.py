# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_n: SpeakerDatabase = {
    "Nexus Center DIY": {
        "brand": "Nexus",
        "model": "Center DIY",
        "type": "passive",
        "price": "",
        "shape": "center",
        "amount": "each",
        "default_measurement": "misc-mtg90",
        "measurements": {
            "misc-mtg90": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "review": "http://www.hificircuit.com/community/threads/project-nexus-a-timbre-matched-family-of-hi-fi-ht-speakers.319/#post-3368",
                "review_published": "20211107",
            },
        },
    },
    "Nexo PS8": {
        "skip": True,
        "brand": "Nexo",
        "model": "PS8",
        "type": "passive",
        "price": "",
        "shape": "center",
        "amount": "each",
        "default_measurement": "vendor-pattern-100x55",
        "measurements": {
            "vendor-pattern-100x55": {
                "origin": "Vendors-Nexo",
                "format": "spl_hv_txt",
                "quality": "low",
                "review_published": "20221106",
            },
        },
    },
    "Nexo PS10": {
        "skip": True,
        "brand": "Nexo",
        "model": "PS10",
        "type": "passive",
        "price": "",
        "shape": "center",
        "amount": "each",
        "default_measurement": "vendor-pattern-100x55",
        "measurements": {
            "vendor-pattern-100x55": {
                "origin": "Vendors-Nexo",
                "format": "spl_hv_txt",
                "quality": "low",
                "review_published": "20221106",
            },
        },
    },
    "Nexo PS15": {
        "skip": True,
        "brand": "Nexo",
        "model": "PS15",
        "type": "passive",
        "price": "",
        "shape": "center",
        "amount": "each",
        "default_measurement": "vendor-pattern-100x55",
        "measurements": {
            "vendor-pattern-100x55": {
                "origin": "Vendors-Nexo",
                "format": "spl_hv_txt",
                "quality": "low",
                "review_published": "20221106",
            },
        },
    },
    "Nexus MT DIY": {
        "brand": "Nexus",
        "model": "MT DIY",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "misc-mtg90",
        "measurements": {
            "misc-mtg90": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "review": "http://www.hificircuit.com/community/threads/project-nexus-a-timbre-matched-family-of-hi-fi-ht-speakers.319/#post-3368",
                "review_published": "20211107",
            },
        },
    },
    "Nexus MTM DIY": {
        "brand": "Nexus",
        "model": "MTM DIY",
        "type": "passive",
        "price": "",
        "shape": "center",
        "amount": "each",
        "default_measurement": "misc-mtg90",
        "measurements": {
            "misc-mtg90": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "review": "http://www.hificircuit.com/community/threads/project-nexus-a-timbre-matched-family-of-hi-fi-ht-speakers.319/#post-3368",
                "review_published": "20211107",
            },
        },
    },
    "Natural Sound NS17": {
        "brand": "Natural Sound",
        "model": "NS17",
        "type": "passive",
        "price": "2300",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/natural-sound-ns17-review-speaker.25251/",
                "review_published": "20210726",
            },
        },
    },
    "Neumann KH 80": {
        "brand": "Neumann",
        "model": "KH 80",
        "type": "active",
        "price": "1000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr-v3-20200711",
        "measurements": {
            # review is here but I do not find the data
            #'asr-v1-20200120' : {
            #    'origin': 'ASR',
            #    'format': 'klippel',
            #    'review': 'https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh-80-dsp-monitor-review.11018/',
            # },
            # that's the working sample
            "asr-v2-20200208": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh-80-dsp-speaker-measurements-take-two.11323/",
            },
            # 3rd measurement later
            "asr-v3-20200711": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh80-dsp-monitor-measurements-3.14637/",
                    "tnw": "https://thenextweb.com/news/these-3-studio-monitors-are-great-speakers-for-a-small-desk",
                    "vendor": "https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh-80-dsp-speaker-measurements-take-two.11323/page-22#post-425237",
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/neumann_kh80/",
                },
                "review_published": "20200711",
            },
            "misc-napilopez": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
            },
            "vendor": {
                "origin": "Vendors-Neumann",
                "format": "webplotdigitizer",
                "quality": "medium",
            },
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review_published": "20240331",
                "specifications": {
                    "size": {
                        "height": 345,
                        "width": 243,
                        "depth": 277,
                    },
                    "weight": 4.1,
                },
            },
        },
    },
    "Neumann KH 120A": {
        "brand": "Neumann",
        "model": "KH 120A",
        "type": "active",
        "price": "2500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "vendor-gll",
        "measurements": {
            "misc-dominikz": {
                "origin": "Misc",
                "format": "rew_text_dump",
                "quality": "low",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh-120a-spinorama-and-misc-measurements.26896/",
                "review_published": "20210926",
            },
            "vendor-klippel": {
                "origin": "Vendors-Neumann",
                "format": "webplotdigitizer",
                "quality": "medium",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh-80-dsp-speaker-measurements-take-two.11323/page-22#post-425238",
            },
            "vendor-gll": {
                "origin": "Vendors-Neumann",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "notes": "data from GLL file: computed at 2m with pink noise broadband",
            },
        },
    },
    "Neumann KH 120 II": {
        "brand": "Neumann",
        "model": "KH 120 II",
        "type": "active",
        "price": "1000",
        "shape": "bookshelves",
        "amount": "each",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh120-ii-monitor-review.46362/",
                "review_published": "20230714",
            },
        },
    },
    "Neumann KH 150": {
        "brand": "Neumann",
        "model": "KH 150",
        "type": "active",
        "price": "3500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?attachments/neumann-kh150-zip.248926/",
                "review_published": "20221210",
                "specifications": {
                    "SPL": {
                        "peak": 118,
                    },
                    "size": {
                        "height": 345,
                        "width": 225,
                        "depth": 273,
                    },
                    "weight": 8.0,
                },
            },
        },
    },
    "Neumann KH 310A": {
        "brand": "Neumann",
        "model": "KH 310A",
        "type": "active",
        "price": "4400",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh-310a-review-powered-monitor.17723/",
                "review_published": "20201120",
            },
            "vendor-gll": {
                "origin": "Vendors-Neumann",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "notes": "data from GLL file: computed at 2m with pink noise broadband",
                "review_published": "20221110",
            },
        },
    },
    "Neumann KH 420G": {
        "brand": "Neumann",
        "model": "KH 420G",
        "type": "active",
        "price": "9000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/neumann-kh420-review-studio-monitor.33529/",
                "review_published": "20220501",
            },
            "vendor": {
                "origin": "Vendors-Neumann",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20220917",
            },
        },
    },
    "Neumi BS5": {
        "brand": "Neumi",
        "model": "BS5",
        "type": "passive",
        "price": "150",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac-v2-20211212-ported",
        "measurements": {
            "eac-v2-20211212-ported": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/neumi_bs5_nfs/",
                    "yt": "https://www.youtube.com/watch?v=NnGbd9hxZe8",
                },
                "review_published": "20211212",
            },
            "eac-v2-20211212-sealed": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/neumi_bs5_nfs/",
                    "yt": "https://www.youtube.com/watch?v=NnGbd9hxZe8",
                },
                "review_published": "20211212",
            },
            "eac-v1-20200620": {
                "origin": "ErinsAudioCorner",
                "format": "webplotdigitizer",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/neumi_bs5/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/neumi-bs5-bookshelf-speaker-review.14404/",
                },
                "review_published": "20200620",
            },
        },
    },
    "Neumi BS5P": {
        "brand": "Neumi",
        "model": "BS5P",
        "type": "active",
        "price": "150",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac-v2-20210519",
        "measurements": {
            "eac-v2-20210519": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/neumi_bs5p_take2/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/revisited-neumi-bs5p-powered-bookshelf-speaker.23522/#post-786588",
                },
                "review_published": "20210519",
                "notes": "Second measurement with a new internal EQ provided by Neumi and ports stuffed",
            },
            "eac-v1-20210417": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/neumi_bs5p/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/neumi-bs5p-powered-bookshelf-speaker-150-pair.22589/",
                },
                "review_published": "20210417",
            },
        },
    },
    "Neumi Silk 4": {
        "brand": "Neumi",
        "model": "Silk 4",
        "type": "passive",
        "price": "150",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/neumi_silk4/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/neumi-silk-4-review-measurements-by-erin.49025/",
                },
                "review_published": "20231106",
                "specifications": {
                    "sensitivity": 85,
                    "impedance": 8,
                    "size": {
                        "height": 208,
                        "width": 140,
                        "depth": 226,
                    },
                    "weight": 2.8,
                },
            },
        },
    },
    "NHT Pro M-00": {
        "brand": "NHT",
        "model": "Pro M-00",
        "type": "active",
        "price": "500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/nht-pro-m-00-powered-monitor-review.10859/",
                "symmetry": "horizontal",
                "review_published": "20200605",
            },
        },
    },
    "NHT C3": {
        "brand": "NHT",
        "model": "C3",
        "type": "passive",
        "price": "600",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/nht-c3-review-3-way-speaker.20287/",
                "review_published": "20210304",
            },
        },
    },
    "NHT SB2": {
        "brand": "NHT",
        "model": "SB2",
        "type": "passive",
        "price": "400",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/nht-sb2-speaker-review.13273/",
                "review_published": "20200512",
            },
        },
    },
    "NHT Super Zero 2.1": {
        "brand": "NHT",
        "model": "Super Zero 2.1",
        "type": "passive",
        "price": "250",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/nht-super-zero-2-1-review-bookshelf-speaker.18643/",
                "review_published": "20201221",
            },
        },
    },
    "Novacoustic KIRA 5": {
        "brand": "Novacoustic",
        "model": "KIRA 5",
        "type": "passive",
        "price": "",
        "shape": "liveportable",
        "amount": "each",
        "default_measurement": "vendor-pattern-90x90",
        "measurements": {
            "vendor-pattern-90x90": {
                "origin": "Vendors-Novacoustic",
                "format": "gll_hv_txt",
                "review_published": "20230402",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "sensitivity": 92,
                    "impedance": 16,
                    "SPL": {
                        "max": 117,
                    },
                    "size": {
                        "height": 160,
                        "width": 160,
                        "depth": 180,
                    },
                    "weight": 3.0,
                },
            },
        },
    },
    "Novacoustic KIRA 8": {
        "brand": "Novacoustic",
        "model": "KIRA 8",
        "type": "passive",
        "price": "",
        "shape": "liveportable",
        "amount": "each",
        "default_measurement": "vendor-pattern-90x90",
        "measurements": {
            "vendor-pattern-90x90": {
                "origin": "Vendors-Novacoustic",
                "format": "gll_hv_txt",
                "review_published": "20230402",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "sensitivity": 96,
                    "impedance": 8,
                    "SPL": {
                        "max": 123,
                    },
                    "size": {
                        "height": 250,
                        "width": 250,
                        "depth": 250,
                    },
                    "weight": 9.0,
                },
            },
        },
    },
    "Novacoustic KIRA 10": {
        "brand": "Novacoustic",
        "model": "KIRA 10",
        "type": "passive",
        "price": "",
        "shape": "liveportable",
        "amount": "each",
        "default_measurement": "vendor-pattern-90x90",
        "measurements": {
            "vendor-pattern-90x90": {
                "origin": "Vendors-Novacoustic",
                "format": "gll_hv_txt",
                "review_published": "20230402",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "sensitivity": 97,
                    "impedance": 8,
                    "SPL": {
                        "max": 128,
                    },
                    "size": {
                        "height": 300,
                        "width": 300,
                        "depth": 300,
                    },
                    "weight": 14,
                },
            },
        },
    },
    "Novacoustic KIRA 12": {
        "brand": "Novacoustic",
        "model": "KIRA 12",
        "type": "passive",
        "price": "",
        "shape": "liveportable",
        "amount": "each",
        "default_measurement": "vendor-pattern-90x90",
        "measurements": {
            "vendor-pattern-90x90": {
                "origin": "Vendors-Novacoustic",
                "format": "gll_hv_txt",
                "review_published": "20230402",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "sensitivity": 98,
                    "impedance": 8,
                    "SPL": {
                        "max": 131,
                    },
                    "size": {
                        "height": 360,
                        "width": 360,
                        "depth": 360,
                    },
                    "weight": 18.5,
                },
            },
        },
    },
    "Novacoustic Pariz P28": {
        "brand": "Novacoustic",
        "model": "Pariz P28",
        "type": "passive",
        "price": "",
        "shape": "liveportable",
        "amount": "each",
        "default_measurement": "vendor-pattern-90x40",
        "measurements": {
            "vendor-pattern-90x40": {
                "origin": "Vendors-Novacoustic",
                "format": "gll_hv_txt",
                "review_published": "20230402",
                "specifications": {
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 40,
                    },
                    "sensitivity": 100,
                    "impedance": 8,
                    "SPL": {
                        "max": 136,
                    },
                    "size": {
                        "height": 590,
                        "width": 270,
                        "depth": 330,
                    },
                    "weight": 18.0,
                },
            },
        },
    },
    "Novacoustic Pariz P412": {
        "brand": "Novacoustic",
        "model": "Pariz P412",
        "type": "passive",
        "price": "",
        "shape": "toursound",
        "amount": "each",
        "default_measurement": "vendor-pattern-110x50",
        "measurements": {
            "vendor-pattern-110x50": {
                "origin": "Vendors-Novacoustic",
                "format": "gll_hv_txt",
                "review_published": "20230402",
                "specifications": {
                    "dispersion": {
                        "horizontal": 110,
                        "vertical": 50,
                    },
                    "sensitivity": 112,
                    "impedance": 2,
                    "SPL": {
                        "max": 149,
                    },
                    "size": {
                        "height": 800,
                        "width": 560,
                        "depth": 570,
                    },
                    "weight": 60.0,
                },
            },
        },
    },
    "Nubert NuVero 60": {
        "brand": "Nubert",
        "model": "NuVero 60",
        "type": "passive",
        "price": "1750",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/nubert-nuvero-60-speaker-review.54390/",
                },
                "review_published": "20240513",
                "specifications": {
                    "sensitivity": 83,
                    "impedance": 4,
                    "size": {
                        "height": 490,
                        "width": 234,
                        "depth": 375,
                    },
                    "weight": 16.0,
                },
            },
        },
    },
}
