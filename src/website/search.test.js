import { global, afterEach, beforeAll, beforeEach, describe, expect, test, it, vi } from 'vitest';
import { urlParameters2Sort } from './search.js';

describe('urlParameters2Sort', () => {

    beforeEach(() => {
    });
    
    afterEach(() => {
    });
    
    it('test sort', () => {
	const url = new URL('https://spinorama.org/index.html?count=20&search=it');
	const params = urlParameters2Sort(url);
	const keywords = params[2];
	expect(params.length).toBe(4);
	expect(keywords).toBe('it');
	expect(params[3].count).toBe(20);
    });
    
});


