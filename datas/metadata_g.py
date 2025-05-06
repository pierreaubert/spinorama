# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

note_genelec_gll = (
    "Data provided by Genelec in GLL format uses 1/3rd octave smoothing and 5 degrees resolution"
)

speakers_info_g: SpeakerDatabase = {
    "Gainphile R16": {
        "brand": "Gainphile",
        "model": "R16",
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
    "Gallo Acoustics A Diva Ti": {
        "brand": "Gallo Acoustics",
        "model": "A Diva Ti",
        "type": "passive",
        "price": "400",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "misc-archimago",
        "measurements": {
            "misc-archimago": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "review": "https://archimago.blogspot.com/2021/05/review-measurements-anthony-gallo.html",
                "quality": "low",
            },
        },
    },
    "Gallo Acoustics Nucleus Micro": {
        "brand": "Gallo Acoustics",
        "model": "Nucleus Micro",
        "type": "passive",
        "price": "300",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "misc-archimago",
        "measurements": {
            "misc-archimago": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "review": "https://archimago.blogspot.com/2021/05/review-measurements-anthony-gallo.html",
                "quality": "low",
            },
        },
    },
    "GedLee Nathan": {
        "brand": "GedLee",
        "model": "Nathan",
        "type": "passive",
        "price": "",
        "shape": "bookshelves",
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
    "Genelec 1031A": {
        "brand": "Genelec",
        "model": "1031A",
        "type": "active",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "misc-audiorekr",
        "measurements": {
            "misc-audiorekr": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "audiorekr": "https://audiore.kr/genelec-1031a-%eb%a6%ac%eb%b7%b0/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-1031a-measurements-review.49907/",
                },
                "data_acquisition": {
                    "min_valid_freq": 200,
                },
                "specifications": {
                    "SPL": {
                        "max": 110,
                        "peak": 120,
                    },
                    "size": {
                        "height": 395,
                        "width": 250,
                        "depth": 290,
                    },
                    "weight": 12.7,
                },
                "review_published": "20250125",
                "notes": "Data is valid above ~200Hz.",
            },
        },
    },
    "Genelec 1032A": {
        "brand": "Genelec",
        "model": "1032A",
        "type": "active",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "misc-tomvg",
        "measurements": {
            "misc-tomvg": {
                "origin": "Misc",
                "format": "rew_text_dump",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-1032a-measurements-including-spinorama.17491/",
                "quality": "low",
                "review_published": "20201112",
                "notes": "data corrected in May 2021",
            },
        },
    },
    "Genelec 4010A": {
        "skip": True,  # quality is too low, bass data is clearly not correct
        "brand": "Genelec",
        "model": "4010A",
        "type": "active",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "notes": "{}".format(note_genelec_gll),
                "review_published": "20220918",
            },
        },
    },
    "Genelec 4020C": {
        "skip": True,  # quality is too low, bass data is clearly not correct
        "brand": "Genelec",
        "model": "4020C",
        "type": "active",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "notes": "{}".format(note_genelec_gll),
                "review_published": "20220918",
            },
        },
    },
    "Genelec 4030C": {
        "skip": True,  # quality is too low, bass data is clearly not correct
        "brand": "Genelec",
        "model": "4030C",
        "type": "active",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "notes": "{}".format(note_genelec_gll),
                "review_published": "20220918",
            },
        },
    },
    "Genelec 4040A": {
        "skip": True,  # quality is too low, bass data is clearly not correct
        "brand": "Genelec",
        "model": "4040A",
        "type": "active",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "low",
                "notes": "{}".format(note_genelec_gll),
                "review_published": "20220918",
            },
        },
    },
    "Genelec 8010A": {
        "brand": "Genelec",
        "model": "8010A",
        "type": "active",
        "price": "600",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8010a-powered-studio-monitor-review.16866/",
            },
        },
    },
    "Genelec 8030A": {
        "brand": "Genelec",
        "model": "8030A",
        "type": "active",
        "shape": "bookshelves",
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
    "Genelec 8030C": {
        "brand": "Genelec",
        "model": "8030C",
        "type": "active",
        "price": "1000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8030c-studio-monitor-review.14795/",
                "specifications": {
                    "SPL": {
                        "peak": 104,
                    },
                    "size": {
                        "height": 299,
                        "width": 189,
                        "depth": 178,
                    },
                    "weight": 5,
                },
            },
        },
    },
    "Genelec 8050B": {
        "brand": "Genelec",
        "model": "8050B",
        "type": "active",
        "price": "3000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8050b-review-studio-monitor.20542/",
                "specifications": {
                    "SPL": {
                        "peak": 104,
                    },
                    "size": {
                        "height": 452,
                        "width": 286,
                        "depth": 278,
                    },
                    "weight": 14.4,
                },
            },
        },
    },
    "Genelec 8320A": {
        "brand": "Genelec",
        "model": "8320A",
        "type": "active",
        "price": "1250",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8320a-review-powered-monitor.23831/",
                "review_published": "20210530",
                "specifications": {
                    "SPL": {
                        "peak": 100,
                    },
                    "size": {
                        "height": 242,
                        "width": 151,
                        "depth": 142,
                    },
                    "weight": 3.2,
                },
            },
        },
    },
    "Genelec 8330A": {
        "brand": "Genelec",
        "model": "8330A",
        "type": "active",
        "price": "1700",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8330a-review-studio-monitor.25704/",
                "review_published": "20210812",
                "specifications": {
                    "SPL": {
                        "peak": 104,
                    },
                    "size": {
                        "height": 299,
                        "width": 189,
                        "depth": 178,
                    },
                    "weight": 6.7,
                },
            },
        },
    },
    "Genelec 8331A": {
        "brand": "Genelec",
        "model": "8331A",
        "type": "active",
        "price": "4500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/genelec_8331a/",
                    "yt": "https://www.youtube.com/watch?v=Ui1Gh_s_sX0",
                },
                "review_published": "20220303",
                "specifications": {
                    "SPL": {
                        "peak": 104,
                    },
                    "size": {
                        "height": 305,
                        "width": 189,
                        "depth": 212,
                    },
                    "weight": 6.7,
                },
            },
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20220918",
                "quality": "low",
                "notes": "{}".format(note_genelec_gll),
            },
        },
    },
    "Genelec 8341A": {
        "brand": "Genelec",
        "model": "8341A",
        "type": "active",
        "price": "4500",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr-vertical",
        "measurements": {
            "asr-vertical": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8341a-sam%E2%84%A2-studio-monitor-review.11652/#post-335087",
                "specifications": {
                    "SPL": {
                        "peak": 110,
                    },
                    "size": {
                        "height": 370,
                        "width": 237,
                        "depth": 243,
                    },
                    "weight": 9.8,
                },
            },
            "asr-horizontal": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8341a-sam%E2%84%A2-studio-monitor-review.11652/#post-335087",
            },
            "misc-napilopez": {
                "origin": "Misc",
                "format": "rew_text_dump",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8341a-spinorama-and-measurements.23463/#post-785643",
                    "tnw": "https://thenextweb.com/news/genelec-8341a-studio-monitor-review",
                },
                "quality": "low",
                "review_published": "20210518",
            },
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20220918",
                "quality": "low",
                "notes": "{}".format(note_genelec_gll),
            },
        },
    },
    "Genelec 8351A": {
        "brand": "Genelec",
        "model": "8351A",
        "type": "active",
        "price": "5700",
        "shape": "bookshelves",
        "amount": "pair",
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
    "Genelec 8351B": {
        "brand": "Genelec",
        "model": "8351B",
        "type": "active",
        "price": "6000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr-vertical",
        "measurements": {
            "asr-vertical": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8351b-review-studio-monitor.23432/",
                "specifications": {
                    "SPL": {
                        "peak": 113,
                    },
                    "size": {
                        "height": 454,
                        "width": 287,
                        "depth": 278,
                    },
                    "weight": 14.3,
                },
            },
            "asr-horizontal": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8351b-review-studio-monitor.23432/",
            },
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "review_published": "20220918",
                "quality": "low",
                "notes": "{}".format(note_genelec_gll),
            },
        },
    },
    "Genelec 8361A": {
        "brand": "Genelec",
        "model": "8361A",
        "type": "active",
        "price": "10000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr-vertical",
        "measurements": {
            "asr-vertical": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8361a-review-powered-monitor.28039/",
                    "sar": "https://www.soundonsound.com/reviews/genelec-8361a",
                    "lbt": "https://www.lbtechreviews.com/test/speakers/genelec-8361a",
                    "pte": "https://www.pro-tools-expert.com/production-expert-1/genelec-8361a-tested",
                    "sos": "https://www.soundonsound.com/reviews/genelec-8361a",
                    "dlm": "https://www.delamar.de/test/genelec-8361a-test/",
                    "lbd": "https://www.lowbeats.de/test-genelec-8361a-und-subwoofer-w371a-aktiv-monitor-dreamteam/",
                },
                "review_published": "20211112",
                "specifications": {
                    "SPL": {
                        "peak": 118,
                    },
                    "size": {
                        "height": 593,
                        "width": 357,
                        "depth": 347,
                    },
                    "weight": 31.9,
                },
            },
            "asr-horizontal": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-8361a-review-powered-monitor.28039/",
                "review_published": "20211112",
            },
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": {
                    "via": "gll",
                    "distance": 1,
                    "signal": "aes 20Hz-20kHz",
                    "resolution": 5,
                    "min_valid_freq": 100,
                    "max_valid_freq": 20000,
                },
                "quality": "low",
                "notes": "{}".format(note_genelec_gll),
                "review_published": "20220918",
            },
        },
    },
    "Genelec G2": {
        "brand": "Genelec",
        "model": "G2",
        "type": "active",
        "price": "600",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "misc-tomvg",
        "measurements": {
            "misc-tomvg": {
                "origin": "Misc",
                "format": "rew_text_dump",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-g2-8020-measurements.18076/#post-588571",
                "quality": "low",
            },
        },
    },
    "Genelec M040": {
        "brand": "Genelec",
        "model": "M040",
        "type": "active",
        "price": "1200",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-m040-review-studio-monitor.36535/",
                "review_published": "20220816",
            },
        },
    },
    "Genelec S360": {
        "brand": "Genelec",
        "model": "S360",
        "type": "active",
        "price": "6800",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/genelec-s360-review-studio-monitor.36187/",
                    "sr": "https://www.soundandrecording.de/equipment/genelec-s360a-high-spl-monitor-im-test/",
                    "sos": "https://www.soundonsound.com/reviews/genelec-s360",
                },
                "review_published": "20220801",
                "specifications": {
                    "SPL": {
                        "peak": 118,
                    },
                    "size": {
                        "height": 530,
                        "width": 360,
                        "depth": 360,
                    },
                    "weight": 30,
                },
            },
            "vendor": {
                "origin": "Vendors-Genelec",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "high",
                "review_published": "20220918",
            },
        },
    },
    "Genius SP-HF3000A": {
        "brand": "Genius",
        "model": "SP-HF3000A",
        "type": "active",
        "price": "",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "misc-dominikz",
        "measurements": {
            "misc-dominikz": {
                "origin": "Misc",
                "format": "rew_text_dump",
                "quality": "low",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/genius-sp-hf3000a-discontinued-powered-pc-loudspeaker-measurements.28332/",
                "review_published": "20211121",
            },
        },
    },
    "GGNTKT M1": {
        "brand": "GGNTKT",
        "model": "M1",
        "shape": "bookshelves",
        "type": "active",
        "price": "5900",
        "amount": "pair",
        "default_measurement": "vendor-v2-202009-monopole",
        "measurements": {
            "vendor-v2-202009-monopole": {
                "origin": "Vendors-GGNTKT",
                "format": "webplotdigitizer",
                "quality": "high",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/ggntkt-model-m1.12959/",
                    "ggntkt": "https://ggntkt.de/model-m1/technische-daten/",
                },
            },
            "vendor-v1-202008": {
                "origin": "Vendors-GGNTKT",
                "format": "webplotdigitizer",
                "quality": "high",
            },
        },
    },
    "GGNTKT M3": {
        "brand": "GGNTKT",
        "model": "M3",
        "shape": "floorstanders",
        "type": "active",
        "price": "22500",
        "amount": "pair",
        "default_measurement": "vendor-v1-202304",
        "measurements": {
            "vendor-v1-202304": {
                "origin": "Vendors-GGNTKT",
                "format": "webplotdigitizer",
                "quality": "medium",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/ggntkt-m3-yes-m3-formerly-known-as-m2.14656",
                },
                "review_published": "20231118",
                "specifications": {
                    "dispersion": {
                        "horizontal": 140,
                        "vertical": 100,
                    },
                    "size": {
                        "height": 1286,
                        "width": 499,
                        "depth": 199,
                    },
                },
            },
        },
    },
    "GoldenEar BRX": {
        "brand": "GoldenEar",
        "model": "BRX",
        "type": "passive",
        "price": "1600",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/goldenear-brx-review-high-end-bookshelf-speaker.28371/",
                    "sav": "https://www.soundandvision.com/content/goldenear-technology-brx-bookshelf-speakers-review",
                    "ste": "https://www.stereophile.com/content/goldenear-brx-bookshelf-reference-x-loudspeaker",
                    "tas": "https://www.theabsolutesound.com/articles/goldenear-brx",
                    "ahc": "https://www.audioholics.com/bookshelf-speaker-reviews/goldenear-brx-bookshelf-speaker",
                },
                "review_published": "20211123",
            },
        },
    },
    "Google Nest Audio": {
        "brand": "Google",
        "model": "Nest Audio",
        "type": "active",
        "price": "90",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/google-nest-audio-speaker-review.58134/",
                    "asr2": "https://www.audiosciencereview.com/forum/index.php?threads/google-nest-audio-spinorama-and-measurements.16464/",
                    "tnw": "https://thenextweb.com/news/review-googles-nest-audio-is-a-legit-good-speaker-and-i-have-the-data-to-prove-it",
                },
                "specifications": {
                    "size": {
                        "height": 175,
                        "width": 124,
                        "depth": 78,
                    },
                    "weight": 1.2,
                },
                "review_published": "20241102",
            },
            "misc-napilopez": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
            },
        },
    },
    "GR Research AV123": {
        "brand": "GR Research",
        "model": "AV123",
        "shape": "center",
        "type": "passive",
        "price": "500",
        "amount": "each",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/av123-gr-research-x-voce-speaker-review.49563/",
                },
                "review_published": "20231116",
            },
        },
    },
    "GR Research NX-Bravo": {
        "brand": "GR Research",
        "model": "NX-Bravo",
        "type": "passive",
        "price": "1525",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac-15-degree",
        "measurements": {
            "eac-15-degree": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "",
                    "yt": "https://youtu.be/g9MsYUONNhg",
                },
                "review_published": "20250404",
		"notes": "Speaker is designed to be listen at a 15 degrees angle.",
                "specifications": {
                    "sensitivity": 87,
                    "impedance": 4.7,
                    "size": {
                        "height": 355,
                        "width": 190,
                        "depth": 292,
                    },
                },
            },
            "eac-0-degree": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "",
                    "yt": "https://youtu.be/g9MsYUONNhg",
                },
                "review_published": "20250404",
		"notes": "Speaker is designed to be listen at a 15 degrees angle. This measurement is on-axis.",
            },
        },
    },

    "GR Research Klipsch RP-600M Upgrade": {
        "brand": "GR Research",
        "model": "Klipsch RP-600M Upgrade",
        "shape": "bookshelves",
        "type": "passive",
        "price": "600",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/gr-research-klipsch-rp-600m-upgrade-review-speaker.35326/",
                    "yt": "https://youtu.be/-eWnYAgiMwQ",
                },
                "review_published": "20220628",
            },
        },
    },
    "GR Research LGK 2.0": {
        "brand": "GR Research",
        "model": "LGK 2.0",
        "shape": "bookshelves",
        "type": "passive",
        "price": "1000",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/gr-research-lgk-2-0-speaker-review-a-joke.34783/",
                    "yt": "https://youtu.be/IikqAg38FPs",
                },
                "review_published": "20220607",
            },
        },
    },
    "GR Research X-LS Encore Kit": {
        "brand": "GR Research",
        "model": "X-LS Encore Kit",
        "shape": "bookshelves",
        "type": "passive",
        "price": "500",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/gr-research-x-ls-encore-kit-speaker-review.14957/",
            },
        },
    },
    "Gradient Helsinki 1.5": {
        "brand": "Gradient",
        "model": "Helsinki 1.5",
        "shape": "floorstanders",
        "type": "passive",
        "price": "",
        "default_measurement": "princeton",
        "measurements": {
            "princeton": {
                "origin": "Princeton",
                "format": "princeton",
                "review": "https://www.princeton.edu/3D3A/Directivity.html",
                "review_published": "20151001",
            },
        },
    },
    "Grimani Systems Alpha": {
        "brand": "Grimani Systems",
        "model": "Alpha",
        "type": "active",
        "price": "",
        "amount": "pair",
        "shape": "inwall",
        "default_measurement": "misc-audioholics",
        "measurements": {
            "misc-audioholics": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://www.youtube.com/watch?v=xqsTFc8MdvA",
                "review_published": "20211118",
            },
        },
    },
    "Grimani Systems Rixos-L": {
        "brand": "Grimani Systems",
        "model": "Rixos-L",
        "type": "active",
        "price": "8200",
        "amount": "each",
        "shape": "inwall",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/grimani-systems-rixos-l-review-active-dsp-speaker.35171/",
                "review_published": "20220623",
            },
        },
    },
    "Grimani Systems Tau": {
        "brand": "Grimani Systems",
        "model": "Tau",
        "type": "active",
        "price": "",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "misc-audioholics",
        "measurements": {
            "misc-audioholics": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://www.youtube.com/watch?v=xqsTFc8MdvA",
                "review_published": "20211118",
            },
        },
    },
}
