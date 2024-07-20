# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_x: SpeakerDatabase = {
    "XMechanik Mechano23 DIY": {
        "brand": "XMechanik",
        "model": "Mechano23 DIY",
        "type": "passive",
        "price": "200",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/mechano23-open-source-diy-speaker-review.54066/",
                    "design": "https://www.audiosciencereview.com/forum/index.php?threads/small-2-way-speakers-with-linear-on-axis-and-power-response-characteristics-scan-speak-and-sb-acoustics-drivers-h-v-off-axis-measurements-included.41757/",
                },
                "review_published": "20240428",
            },
        },
    },
    "XSA Labs Vanguard": {
        "brand": "XSA Labs",
        "model": "Vanguard",
        "type": "passive",
        "price": "1000",
        "shape": "bookshelves",
        "amount": "pair",
        "default_measurement": "asr",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/xsa-labs-vanguard-speaker-review.46629/",
                    "diy": "https://www.diyaudio.com/community/threads/vanguard-speaker.388184/",
                },
                "review_published": "20230723",
            },
        },
    },
    "XTZ Spirit 4": {
        "brand": "XTZ",
        "model": "Spirit 4",
        "type": "passive",
        "shape": "bookshelves",
        "price": "477",
        "amount": "pair",
        "default_measurement": "misc-ageve",
        "measurements": {
            "misc-ageve": {
                "origin": "Misc",
                "format": "spl_hv_txt",
                "quality": "low",
                "reviews": {
                    "asr": "https://www.audiosciencereview.com/forum/index.php?threads/xtz-spirit-4-spinorama-measurements-cta-2034.55433/",
                },
                "review_published": "20240707",
                "specifications": {
                    "sensitivity": 86,
                    "impedance": 4,
                    "size": {
                        "height": 350,
                        "width": 190,
                        "depth": 270,
                    },
                    "weight": 8.1,
                },
            },
        },
    },
}
