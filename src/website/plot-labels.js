// Shared display labels. This module intentionally has no graph or
// configuration dependencies: both plot.js and plot-config.js need it during
// their initialisation.
export const labelShort = {
    'Linear Regression': 'Reg',
    'Band ±1.5dB': '±1.5dB',
    'Band ±3dB': '±3dB',
    'Estimated In-Room Response': 'PIR',
    'On Axis': 'ON',
    'Listening Window': 'LW',
    'Early Reflections': 'ER',
    'Sound Power': 'SP',
    'Early Reflections DI': 'ERDI',
    'Sound Power DI': 'SPDI',
    'Ceiling Bounce': 'CB',
    'Floor Bounce': 'FB',
    'Front Wall Bounce': 'FWB',
    'Rear Wall Bounce': 'RWB',
    'Side Wall Bounce': 'SWB',
    'Ceiling Reflection': 'CR',
    'Floor Reflection': 'FR',
    Front: 'F',
    Rear: 'R',
    Side: 'S',
    'Total Early Reflection': 'TER',
    'Total Horizontal Reflection': 'THR',
    'Total Vertical Reflection': 'TVR',
};

export const labelLong = Object.entries(labelShort).reduce((labels, [long, short]) => {
    labels[short] = long;
    return labels;
}, {});
