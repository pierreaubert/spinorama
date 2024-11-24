# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_s: SpeakerDatabase = {
    "Sigberg Audio Manta": {
        "brand": "Sigberg Audio",
        "model": "Manta",
        "type": "active",
        "price": "5500",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "vendor-v1-20231028",
        "measurements": {
            "vendor-v1-20231028": {
                "origin": "Vendors-Sigberg Audio",
                "format": "spl_hv_txt",
                "quality": "medium",
                "review_published": "20231207",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/sigberg-audio-manta-12-wideband-cardioid-active-speakers-prototype-build-thread.28255/",
                    "sigbergaudio": "https://www.sigbergaudio.no/blogs/news/interview-with-christer-krogh-head-engineer-of-velvet-recording",
                    "hifipig": "https://www.hifipig.com/sigberg-audio-manta/",
                },
                "specifications": {
                    "SPL": {
                        "peak": 122,
                    },
                    "size": {
                        "height": 600,
                        "width": 360,
                        "depth": 350,
                    },
                    "weight": 25,
                },
            },
        },
    },
    "Sigberg Audio SBS.1": {
        "brand": "Sigberg Audio",
        "model": "SBS.1",
        "type": "active",
        "price": "2500",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "vendor-v2",
        "measurements": {
            "vendor-v2": {
                "origin": "Vendors-Sigberg Audio",
                "format": "spl_hv_txt",
                "quality": "medium",
                "review_published": "20231028",
                "notes": "Klippel generated data",
                "reviews": {
                    "ahl": "https://www.audioholics.com/bookshelf-speaker-reviews/sigberg-audio-sbs.1-1",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/sigberg-audio-sbs-1-active-speakers-prototype-build-thread.20141/",
                },
                "specifications": {
                    "SPL": {
                        "peak": 116,
                    },
                    "size": {
                        "height": 410,
                        "width": 190,
                        "depth": 230,
                    },
                    "weight": 9.5,
                },
            },
            # removed since the v2 is higher quality
            # "vendor-v1": {
            #    "origin": "Vendors-Sigberg Audio",
            #    "format": "rew_text_dump",
            #    "quality": "low",
            #    "review_published": "20230223",
            # },
        },
    },
    "Salk WoW1": {
        "brand": "Salk",
        "model": "WoW1",
        "type": "passive",
        "price": "1295",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/salk-wow1-bookshelf-speaker-review.14842/",
                "review_published": "20200721",
            },
        },
    },
    "Sanders Sound Systems Model 11": {
        "brand": "Sanders Sound Systems",
        "model": "Model 11",
        "type": "passive",
        "price": "",
        "shape": "panel",
        "default_measurement": "princeton-factory",
        "measurements": {
            "princeton-factory": {
                "origin": "Princeton",
                "format": "princeton",
                "symmetry": "horizontal",
                "review": "https://www.princeton.edu/3D3A/Directivity.html",
                "review_published": "20151001",
            },
            "princeton-with-anechoic-foam": {
                "origin": "Princeton",
                "format": "princeton",
                "symmetry": "horizontal",
                "review": "https://www.princeton.edu/3D3A/Directivity.html",
                "review_published": "20151001",
            },
            "princeton-with-backwave-absorber": {
                "origin": "Princeton",
                "format": "princeton",
                "symmetry": "horizontal",
                "review": "https://www.princeton.edu/3D3A/Directivity.html",
                "review_published": "20151001",
            },
        },
    },
    "Seeburg K20": {
        "brand": "Seeburg",
        "model": "K20",
        "type": "passive",
        "price": "4300",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-Seeburg",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221022",
            },
        },
    },
    "Seeburg X1": {
        "brand": "Seeburg",
        "model": "X1",
        "type": "passive",
        "price": "1800",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-Seeburg",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221022",
            },
        },
    },
    "Seeburg X2": {
        "brand": "Seeburg",
        "model": "X2",
        "type": "passive",
        "price": "2200",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-Seeburg",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221022",
            },
        },
    },
    "Seeburg X4": {
        "brand": "Seeburg",
        "model": "X4",
        "type": "passive",
        "price": "2800",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor-pattern-90x60",
        "measurements": {
            "vendor-pattern-90x60": {
                "origin": "Vendors-Seeburg",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221022",
            },
        },
    },
    "Seeburg X6": {
        "brand": "Seeburg",
        "model": "X6",
        "type": "passive",
        "price": "4300",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor-pattern-80x60",
        "measurements": {
            "vendor-pattern-80x60": {
                "origin": "Vendors-Seeburg",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221022",
            },
        },
    },
    "Seeburg X8": {
        "brand": "Seeburg",
        "model": "X8",
        "type": "passive",
        "price": "4500",
        "shape": "liveportable",
        "amount": "pair",
        "default_measurement": "vendor-pattern-80x60",
        "measurements": {
            "vendor-pattern-80x60": {
                "origin": "Vendors-Seeburg",
                "format": "gll_hv_txt",
                "data_acquisition": gll_data_acquisition_std,
                "quality": "medium",
                "review_published": "20221022",
            },
        },
    },
    "Selah Audio Integrity DIY": {
        "brand": "Selah Audio",
        "model": "Integrity DIY",
        "type": "passive",
        "price": "700",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/selah-integrity-diy-speaker-kit-review.15695/",
                "review_published": "20200830",
            },
        },
    },
    "Selah Audio Purezza": {
        "brand": "Selah Audio",
        "model": "Purezza",
        "type": "passive",
        "shape": "bookshelves",
        "price": "2700",
        "default_measurement": "eac-original",
        "measurements": {
            "eac-original": {
                "origin": "ErinsAudioCorner",
                "format": "spl_hv_txt",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/selah_audio_purezza/",
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/selah-audio-purezza-review.15850/",
                },
            },
            "eac-eq": {
                "origin": "ErinsAudioCorner",
                "format": "spl_hv_txt",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/selah_audio_purezza/",
            },
        },
    },
    "Selah Audio RC3R": {
        "brand": "Selah Audio",
        "model": "RC3R",
        "type": "passive",
        "price": "1300",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/selah-audio-rc3r-3-way-speaker-review.11218/",
                "review_published": "20200201",
            },
        },
    },
    "Sehlin Helium DIY": {
        "brand": "Sehlin",
        "model": "Helium DIY",
        "type": "passive",
        "price": "140",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/sehlin-helium-diy-speaker-review.15518/",
                "review_published": "20200822",
            },
        },
    },
    "SONBS SD-10E": {
        "brand": "SONBS",
        "model": "SD-10E",
        "type": "passive",
        "price": "100",
        "amount": "each",
        "shape": "toursound",
        "default_measurement": "vendor",
        "measurements": {
            "vendor": {
                "origin": "Vendors-SONBS",
                "format": "gll_hv_txt",
                "quality": "high",
                "review_published": "20230914",
                "data_acquisition": gll_data_acquisition_std,
            },
        },
    },
    "Sonos Five": {
        "brand": "Sonos",
        "model": "Five",
        "type": "active",
        "price": "650",
        "amount": "each",
        "shape": "omnidirectional",
        "default_measurement": "asr-horizontal",
        "measurements": {
            "asr-horizontal": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/sonos-five-smart-speaker-review.51409/",
                },
                "review_published": "20240116",
                "specifications": {
                    "size": {
                        "height": 203,
                        "width": 364,
                        "depth": 154,
                    },
                    "weight": 6.3,
                },
                "notes": "Since the speaker is almost omnidirectional, it is unclear if the automatic EQ is helping or not. Do not blindly use it and do some listenting",
            },
            "asr-vertical": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/sonos-five-smart-speaker-review.51409/",
                },
                "review_published": "20240116",
                "specifications": {
                    "size": {
                        "height": 203,
                        "width": 364,
                        "depth": 154,
                    },
                    "weight": 6.3,
                },
                "notes": "Since the speaker is almost omnidirectional, it is unclear if the automatic EQ is helping or not. Do not blindly use it and do some listenting",
            },
        },
    },
    "Sonos Move": {
        "brand": "Sonos",
        "model": "Move",
        "type": "active",
        "price": "400",
        "amount": "each",
        "shape": "omnidirectional",
        "default_measurement": "misc-napilopez",
        "measurements": {
            "misc-napilopez": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/sonos-move-on-and-off-axis-measurements-an-interesting-case-study.10625/#post-410956",
                    "tnw": "https://thenextweb.com/news/measured-how-the-sonos-move-balances-performance-and-durability-in-a-bluetooth-speaker?amp=1",
                },
            },
        },
    },
    "Sonos Roam": {
        "brand": "Sonos",
        "model": "Roam",
        "type": "active",
        "price": "179",
        "amount": "each",
        "shape": "omnidirectional",
        "default_measurement": "misc-napilopez",
        "measurements": {
            "misc-napilopez": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/sonos-roam-portable-speaker-spinorama-and-measurements-more-proof-mainstream-speakers-can-be-real-good.23433/",
                    "tnw": "https://thenextweb.com/news/the-sonos-roam-is-an-excellent-bluetooth-speaker-and-weve-got-the-data-to-prove-it",
                },
            },
        },
    },
    "Sonus Faber Lumina II": {
        "brand": "Sonus Faber",
        "model": "Lumina II",
        "type": "passive",
        "price": "1300",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/sonus_faber_lumina_ii/",
                    "yt": "https://youtu.be/Q1RdxgLwnHc?si=mcKDc-XByFdDt8OK",
                },
                "review_published": "20231212",
                "specifications": {
                    "sensitivity": 86,
                    "impedance": 4,
                    "size": {
                        "height": 304,
                        "width": 180,
                        "depth": 263,
                    },
                    "weight": 5.65,
                },
            },
        },
    },
    "Sonus Faber Picolo": {
        "brand": "Sonus Faber",
        "model": "Picolo",
        "type": "passive",
        "price": "585",
        "amount": "each",
        "shape": "center",
        "default_measurement": "misc-ageve",
        "measurements": {
            "misc-ageve": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/sonus-faber-piccolo-solo-spinorama-measurements-cta-2034.58107/",
                    "snv": "https://www.soundandvision.com/content/sonus-faber-concerto-speaker-system-page-2",
                },
                "review_published": "20241102",
                # partial measurements
                "symmetry": "coaxial",
                "specifications": {
                    "sensitivity": 86,
                    "impedance": 8,
                    "size": {
                        "height": 170,
                        "width": 485,
                        "depth": 235,
                    },
                    "weight": 10.0,
                },
            },
        },
    },
    "Sonus Faber Sonetto II": {
        "brand": "Sonus Faber",
        "model": "Sonetto II",
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
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/sonus-faber-sonetto-ii-measurements-now-with-a-spinorama.10727/#post-305705",
                },
            },
        },
    },
    "Sony SS-CS3": {
        "brand": "Sony",
        "model": "SS-CS3",
        "type": "passive",
        "price": "450",
        "shape": "floorstanders",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/sony_sscs3_tower/",
                    "yt": "https://youtu.be/RSnHZ0w3UjI",
                },
                "review_published": "20240115",
                "specifications": {
                    "impedance": 6,
                    "size": {
                        "height": 922,
                        "width": 230,
                        "depth": 260,
                    },
                    "weight": 11.5,
                },
            },
        },
    },
    "Sony SS-CS5": {
        "brand": "Sony",
        "model": "SS-CS5",
        "type": "passive",
        "price": "150",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/sony_sscs5/",
                "review_published": "20200523",
            },
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/sony-ss-cs5-3-way-speaker-review.13562/",
                "review_published": "20200523",
            },
        },
    },
    "SoundArtist LS3|5A": {
        "brand": "SoundArtist",
        "model": "LS3|5A",
        "type": "passive",
        "price": "630",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/soundartist-bbc-ls3-5a-speaker-review.49833/",
                "review_published": "20231125",
            },
        },
    },
    "Soundkraft Enigma BT": {
        "brand": "Soundkraft",
        "model": "Enigma BT",
        "type": "active",
        "price": "500",
        "shape": "bookshelves",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/soundkraft-enigma-bt-speaker-review.35641/",
                "review_published": "20220711",
            },
        },
    },
    "Speakercraft AIM8 One": {
        "brand": "Speakercraft",
        "model": "AIM8 One",
        "type": "passive",
        "price": "",
        "amount": "pair",
        "shape": "inwall",
        "default_measurement": "misc-speakerdata2034",
        "measurements": {
            "misc-speakerdata2034": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "quality": "low",
                "review": "https://speakerdata2034.blogspot.com/2020/04/various-brands-spinorama-data-from.html",
            },
        },
    },
    "Spendor Audio Systems SA1": {
        "brand": "Spendor Audio",
        "model": "Systems SA1",
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
            "misc-archimago": {
                "origin": "Misc",
                "format": "webplotdigitizer",
                "review": "https://archimago.blogspot.com/2021/02/retro-measure-spendor-sa1-1976-monitor.html",
                "quality": "low",
            },
        },
    },
    "SVS Prime Bookshelf": {
        "brand": "SVS",
        "model": "Prime Bookshelf",
        "type": "passive",
        "price": "600",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/svs_prime_bookshelf/",
                "review_published": "20221116",
            },
        },
    },
    "SunAudio Purified 4 4XA25A Fiber+Alu": {
        "brand": "SunAudio",
        "model": "Purified 4 4XA25A Fiber+Alu",
        "type": "passive",
        "price": "3300",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor-v2-20240613",
        "measurements": {
            "vendor-v2-20240613": {
                "origin": "Vendors-SunAudio",
                "format": "spl_hv_txt",
                "quality": "high",  # klippel measurements by https://www.dausend-acoustics.com/
                "review": "https://sunaudio.com/products/purified-4-modular-active-loudspeakers",
                "review_published": "20240613",
                "notes": "Version with 25mm aluminium tweeter (BlieSMa T25A-6 tweeter) and paper fiber woofer (Purifi PTT4.0X04-NLC-02). Crossovers are at 2200Hz and 4000Hz. Measurements are done with a Klippel NFS from https://www.dausend-acoustics.com/",
            },
        },
    },
    "SunAudio Purified 4 4XA25A Alu+Alu": {
        "brand": "SunAudio",
        "model": "Purified 4 4XA25A Alu+Alu",
        "type": "passive",
        "price": "3300",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor-v3-20240619",
        "measurements": {
            "vendor-v3-20240619": {
                "origin": "Vendors-SunAudio",
                "format": "spl_hv_txt",
                "quality": "high",  # klippel measurements by https://www.dausend-acoustics.com/
                "review": "https://sunaudio.com/products/purified-4-modular-active-loudspeakers",
                "review_published": "20240619",
                "notes": "Version with 25mm aluminium tweeter (BlieSMa T25A-6 tweeter) and aluminium woofer (Purifi PTT4.0X04-NLC-04). Crossovers are at 2200Hz and 4145Hz. Measurements are done with a Klippel NFS from https://www.dausend-acoustics.com/",
            },
        },
    },
    "SunAudio Purified 4 4XA25A tw35mm": {
        "brand": "SunAudio",
        "model": "Purified 4 4XA25A tw35mm",
        "type": "passive",
        "price": "2800",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor-v1-20240218",
        "measurements": {
            "vendor-v1-20240218": {
                "origin": "Vendors-SunAudio",
                "format": "spl_hv_txt",
                "quality": "high",  # klippel measurements by https://www.dausend-acoustics.com/
                "review": "https://sunaudio.com/products/purified-4-modular-active-loudspeakers",
                "review_published": "20240218",
                "data_acquisition": {
                    "distance": 3.0,
                },
                "notes": "Sun Audio Purified 4 XP25A with a 35mm tweeter: crossover: Woofer: BW12 @ 1495Hz Tweeter: BW18 @ 2201Hz. Measurements are done at 3m",
            },
        },
    },
    "SunAudio Purified 4 4XA25B Alu+Berryllium": {
        "brand": "SunAudio",
        "model": "Purified 4 4XA25B Alu+Berryllium",
        "type": "passive",
        "price": "3650",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor-v1-20240730",
        "measurements": {
            "vendor-v1-20240730": {
                "origin": "Vendors-SunAudio",
                "format": "spl_hv_txt",
                "quality": "high",  # klippel measurements by https://www.dausend-acoustics.com/
                "review": "https://sunaudio.com/products/purified-4-modular-active-loudspeakers?variant=47286699491674",
                "review_published": "20240730",
                "data_acquisition": {
                    "distance": 2.5,
                },
                "notes": "Crossover Woofer: BW12 @ 2158Hz Tweeter: BW12 @ 4146Hz. Measurements done at 2.5 meter.",
            },
        },
    },
    "SunAudio Purified 4 4XP25B Fiber+Berryllium": {
        "brand": "SunAudio",
        "model": "Purified 4 4XP25B Fiber+Berryllium",
        "type": "passive",
        "price": "3650",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "vendor-v1-20240730",
        "measurements": {
            "vendor-v1-20240730": {
                "origin": "Vendors-SunAudio",
                "format": "spl_hv_txt",
                "quality": "high",  # klippel measurements by https://www.dausend-acoustics.com/
                "review": "https://sunaudio.com/products/purified-4-modular-active-loudspeakers?variant=47286699327834",
                "review_published": "20240730",
                "data_acquisition": {
                    "distance": 2.5,
                },
                "notes": "Sun Audio Purified 4 XP25B Woofer: BW12 @ 2126Hz Tweeter: BW12 @ 4157Hz. Measurements done at 2.5 meter.",
            },
        },
    },
    "SVS Prime Center": {
        "brand": "SVS",
        "model": "Prime Center",
        "type": "passive",
        "price": "400",
        "shape": "center",
        "amount": "each",
        "default_measurement": "eac-horizontal",
        "measurements": {
            "eac-horizontal": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/svs_prime_center_channel/",
                "review_published": "20220110",
            },
            "eac-vertical": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/svs_prime_center_channel/",
                "review_published": "20220110",
            },
        },
    },
    "SVS Ultra Bookshelf": {
        "brand": "SVS",
        "model": "Ultra Bookshelf",
        "type": "passive",
        "price": "1000",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "review": "https://www.erinsaudiocorner.com/loudspeakers/svs_ultra_bookshelf/",
                "review_published": "20230312",
            },
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/svs-ultra-bookshelf-speaker-review.15055/",
                "review_published": "20200801",
            },
        },
    },
    "SVS Ultra Evolution Pinnacle Tower": {
        "brand": "SVS",
        "model": "Ultra Evolution Pinnacle Tower",
        "type": "passive",
        "price": "5000",
        "amount": "pair",
        "shape": "floorstanders",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/svs_ultra_evolution_pinnacle/",
                    "yt": "https://youtu.be/mpsg7coXals",
                },
                "review_published": "20240727",
                "specifications": {
                    "sensitivity": 88,
                    "size": {
                        "height": 1260,
                        "width": 300,
                        "depth": 460.7,
                    },
                    "weight": 43.9,
                },
            },
        },
    },
    "Shivaudyo Point Zero": {
        "brand": "Shivaudyo",
        "model": "Point Zero",
        "type": "active",
        "price": "6500",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "https://www.erinsaudiocorner.com/loudspeakers/shivaudyo_point_zero/",
                    "yt": "https://youtu.be/ItAwcW-3Kv4",
                },
                "review_published": "20240414",
                "specifications": {
                    "SPL": {
                        "peak": 110,
                    },
                    "size": {
                        "height": 400,
                        "width": 290,
                        "depth": 390,
                    },
                    "weight": 16.5,
                },
            },
        },
    },
    "System One S-15B": {
        "brand": "System One",
        "model": "S-15B",
        "type": "passive",
        "price": "130",
        "amount": "pair",
        "shape": "bookshelves",
        "default_measurement": "misc-ageve",
        "measurements": {
            "misc-ageve": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/system-one-s15b-spinorama-measurements-cta-2034.58759/",
                },
                "review_published": "20241124",
                "notes": "Tweeter polarity was fixed before measuring. Out of the box, the speaker is worse!",
                "specifications": {
                    "sensitivity": 86,
                    "impedance": 4,
                    "size": {
                        "height": 300,
                        "width": 185,
                        "depth": 225,
                    },
                    "weight": 3.25,
                },
            },
        },
    },

}
