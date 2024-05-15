import { global, afterEach, beforeAll, beforeEach, describe, expect, test, it, vi } from 'vitest';
import { isVertical, isCompact, computeDims } from './plot.js';

function graph_ratio(width, height) {
    width = Math.round(width);
    height = Math.round(height);
    let ratio = (height / width);
    if (width > height) {
	ratio = (width / height);
    }
    return ratio;
}

const screens = {
    'iPhone SE':          {width:  375, height:  667},
    'iPhone 14 Pro Max':  {width:  430, height:  932},
    'Samsung Galaxy S8+': {width:  360, height:  740},
    'iPad Pro':           {width: 1024, height: 1366},
    '16:9 2k':            {width: 1920, height: 1080},
    '16:9 4k':            {width: 3840, height: 2160},
};

describe('computeDims', () => {
    
    Object.entries(screens).forEach( ([name, model]) => {
	it('testing '+name+' vertical compact 2', () => {
	    const [width, height] = [...computeDims(model.width, model.height, true, true, 2)];
	    
	    const pWidth = width/model.width-1.0;
	    expect(pWidth).toBeCloseTo(0, 1);
	    
	    const ratio = graph_ratio(width, height);
	    expect(ratio).toBeGreaterThan(1.0);
	    expect(ratio).toBeLessThan(1.8);
	});
    });
    
    Object.entries(screens).forEach( ([name, model]) => {
	it('testing '+name+' vertical compact 1', () => {
	    const [width, height] = [...computeDims(model.width, model.height, true, true, 1)];
	    
	    const pWidth = width/model.width-1.0;
	    expect(pWidth).toBeCloseTo(0, 1);
	    
	    const ratio = graph_ratio(width, height);
	    expect(ratio).toBeGreaterThan(1.0);
	    expect(ratio).toBeLessThan(1.8);
	});
    });
    
});


