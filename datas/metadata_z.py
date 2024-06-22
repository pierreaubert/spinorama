from . import SpeakerDatabase, gll_data_acquisition_std

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
}
