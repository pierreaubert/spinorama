# -*- coding: utf-8 -*-
"""a list of measurements that are known to be incomplete.
The set is used to decrease verbosity of warnings.
"""

known_incomplete_measurements = set(
    [
        ("Andersson HIS 2.1", "misc-ageve"),
        ("Buchardt Audio S300", "misc-speakerdata2034"),  # missing ER
        ("Buchardt Audio S400", "vendor"),  # missing ER
        ("JBL LSR308", "misc-speakerdata2034"),  # missing LW
        ("KEF R11", "misc-speakerdata2034"),  # only ON and LW
        ("Paradigm Millenia LP 2", "misc-matthews"),
        ("Polk Audio Legend L800", "audioholics"),  # missing SP
    ]
)
