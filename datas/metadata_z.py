# -*- coding: utf-8 -*-
from . import SpeakerDatabase

speakers_info_z: SpeakerDatabase = {
    "Zaph Audio ZA5.2": {
        "brand": "Zaph Audio",
        "model": "ZA5.2",
        "type": "passive",
        "price": "350",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "review": "https://www.audiosciencereview.com/forum/index.php?threads/zaph-audio-za5-2-diy-kit-speaker-review.12086/",
                "review_published": "20201317",
            },
        },
    },
    "Zu Audio Method": {
        "brand": "Zu Audio",
        "model": "Method",
        "type": "passive",
        "price": "700",
        "amount": "each",
        "shape": "bookshelves",
        "default_measurement": "eac",
        "measurements": {
            "eac": {
                "origin": "ErinsAudioCorner",
                "format": "klippel",
                "reviews": {
                    "eac": "",
                    "yt": "",
                },
                "review_published": "20250918",
                "specifications": {
                    "sensitivity": 94,
                    "impedance": 8,
                    "dispersion": {
                        "horizontal": 90,
                        "vertical": 90,
                    },
                    "SPL": {
                        "peak": 110,
                    },
                    "size": {
                        "height": 381,
                        "width": 222,
                        "depth": 280,
                    },
                    "weight": 9,
                },
            },
        },
    },

}
