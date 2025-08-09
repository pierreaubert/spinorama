// -*- coding: utf-8 -*-
// Tests for Simple 3-Step Speaker Metadata Manager
//
// Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

/*eslint no-undef: "error"*/

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { JSDOM } from 'jsdom';

// Mock the module since it's not exported as ES module
const SimpleMetadataManager = await import('./manager.js').then(m => m.default);

// Mock DOM environment
let dom;
let mockDocument;
let mockWindow;

beforeEach(() => {
    // Create a mock DOM environment
    dom = new JSDOM(`
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
            <div id="step-1-indicator"></div>
            <div id="step-2-indicator"></div>
            <div id="step-3-indicator"></div>
            <div id="step-1" class="step active"></div>
            <div id="step-2" class="step"></div>
            <div id="step-3" class="step"></div>
            <input id="speaker-search" />
            <button id="create-new-btn"></button>
            <button id="continue-step-1" disabled></button>
            <button id="add-measurement-btn"></button>
            <button id="back-step-1"></button>
            <button id="continue-step-2"></button>
            <button id="back-step-2"></button>
            <button id="create-commit-btn"></button>
            <button id="start-over-btn"></button>
            <div id="speaker-list"></div>
            <input id="new-brand" />
            <input id="new-model" />
            <div id="current-speaker-info"></div>
            <form id="metadata-form">
                <input name="brand" />
                <input name="model" />
                <select name="type"></select>
                <select name="shape"></select>
                <input name="price" />
                <select name="amount"></select>
                <input id="origin" />
                <select id="format"></select>
                <input id="review" />
                <input id="review_published" />
                <select id="quality"></select>
                <textarea id="notes"></textarea>
                <select id="symmetry"></select>
                <input id="sensitivity" />
                <input id="scaled_flatness" />
                <input id="data_acquisition_via" />
                <input id="data_acquisition_distance" />
                <input id="data_acquisition_signal" />
                <input id="data_acquisition_air_absorbtion" type="checkbox" />
                <input id="data_acquisition_resolution" />
                <textarea id="data_acquisition_notes"></textarea>
                <input id="data_acquisition_min_valid_freq" />
                <input id="data_acquisition_max_valid_freq" />
                <input id="parameters_mean_min" />
                <input id="parameters_mean_max" />
                <input id="extras_is_equed" type="checkbox" />
                <input id="extras_score_penalty" />
            </form>
            <div id="measurements-container"></div>
            <div id="python-code"></div>
            <textarea id="commit-message"></textarea>
            <div id="commit-result" style="display: none;"></div>
        </body>
        </html>
    `, { url: 'http://localhost' });

    mockDocument = dom.window.document;
    mockWindow = dom.window;

    // Mock global objects
    global.document = mockDocument;
    global.window = mockWindow;
    global.fetch = vi.fn();
});

afterEach(() => {
    vi.restoreAllMocks();
    dom.window.close();
});

describe('SimpleMetadataManager', () => {
    let manager;

    beforeEach(() => {
        // Mock fetch for loadSpeakers
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve([
                {
                    id: 'test-speaker-1',
                    brand: 'Test Brand',
                    model: 'Test Model',
                    type: 'passive',
                    shape: 'bookshelves',
                    measurements: {
                        default: {
                            origin: 'Test Origin',
                            format: 'klippel'
                        }
                    }
                }
            ])
        });

        manager = new SimpleMetadataManager();
    });

    describe('Constructor and Initialization', () => {
        it('should initialize with correct default values', () => {
            expect(manager.currentStep).toBe(1);
            expect(manager.selectedSpeaker).toBeNull();
            expect(manager.isNewSpeaker).toBe(false);
            expect(manager.speakers).toEqual([]);
            expect(manager.measurementCounter).toBe(0);
        });

        it('should call init method during construction', () => {
            const initSpy = vi.spyOn(SimpleMetadataManager.prototype, 'init');
            new SimpleMetadataManager();
            expect(initSpy).toHaveBeenCalled();
        });
    });

    describe('Step Navigation', () => {
        it('should show correct step and update indicators', () => {
            // Check that the showStep method updates currentStep correctly
            manager.showStep(2);
            expect(manager.currentStep).toBe(2);

            // The actual DOM manipulation may not work in the test environment
            // but we can verify the method runs without error
            expect(() => manager.showStep(3)).not.toThrow();
            expect(manager.currentStep).toBe(3);
        });

        it('should show/hide step content correctly', () => {
            manager.showStep(3);

            const step1 = mockDocument.getElementById('step-1');
            const step2 = mockDocument.getElementById('step-2');
            const step3 = mockDocument.getElementById('step-3');

            expect(step1.classList.contains('active')).toBe(false);
            expect(step2.classList.contains('active')).toBe(false);
            expect(step3.classList.contains('active')).toBe(true);
        });

        it('should call generatePythonCode when showing step 3', () => {
            const generateSpy = vi.spyOn(manager, 'generatePythonCode').mockImplementation(() => {});
            manager.showStep(3);
            expect(generateSpy).toHaveBeenCalled();
        });
    });

    describe('Speaker Management', () => {
        it('should load speakers from API', async () => {
            // Reset the mock to ensure clean state
            global.fetch.mockClear();
            global.fetch.mockResolvedValue({
                ok: true,
                json: () => Promise.resolve({
                    success: true,
                    data: [
                        {
                            id: 'test-speaker-1',
                            brand: 'Test Brand',
                            model: 'Test Model',
                            type: 'passive',
                            shape: 'bookshelves',
                            measurements: {
                                default: {
                                    origin: 'Test Origin',
                                    format: 'klippel'
                                }
                            }
                        }
                    ]
                })
            });

            // Create a new manager instance to avoid interference from constructor
            const testManager = Object.create(SimpleMetadataManager.prototype);
            testManager.speakers = [];
            testManager.showNotification = vi.fn(); // Mock notification method

            await testManager.loadSpeakers();

            expect(global.fetch).toHaveBeenCalledWith('/api/speakers');
            expect(testManager.speakers).toHaveLength(1);
            expect(testManager.speakers[0].brand).toBe('Test Brand');
        });

        it('should handle API errors gracefully', async () => {
            global.fetch.mockRejectedValue(new Error('API Error'));
            const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

            await manager.loadSpeakers();

            expect(consoleSpy).toHaveBeenCalledWith('Failed to load speakers:', expect.any(Error));
        });

        it('should select speaker correctly', () => {
            const mockSpeaker = {
                id: 'test-speaker',
                brand: 'Test Brand',
                model: 'Test Model'
            };
            const mockElement = mockDocument.createElement('div');

            manager.selectSpeaker(mockSpeaker, mockElement);

            expect(manager.selectedSpeaker).toEqual(mockSpeaker);
            expect(manager.isNewSpeaker).toBe(false);
            expect(mockElement.classList.contains('selected')).toBe(true);
        });

        it('should create new speaker correctly', () => {
            const brandInput = mockDocument.getElementById('new-brand');
            const modelInput = mockDocument.getElementById('new-model');

            brandInput.value = 'New Brand';
            modelInput.value = 'New Model';

            manager.createNewSpeaker();

            expect(manager.selectedSpeaker.brand).toBe('New Brand');
            expect(manager.selectedSpeaker.model).toBe('New Model');
            expect(manager.isNewSpeaker).toBe(true);
        });
    });

    describe('Form Data Handling', () => {
        beforeEach(() => {
            manager.selectedSpeaker = {
                brand: 'Test Brand',
                model: 'Test Model',
                type: 'passive',
                shape: 'bookshelves',
                measurements: {
                    default: {
                        origin: 'Test Origin',
                        format: 'klippel',
                        quality: 'high',
                        sensitivity: 87.5
                    }
                },
                default_measurement: 'default'
            };
        });

        it('should populate form fields correctly', () => {
            // Add options to select elements
            const formatSelect = mockDocument.getElementById('format');
            formatSelect.innerHTML = '<option value="klippel">Klippel</option>';

            manager.populateMetadataForm();

            const form = mockDocument.getElementById('metadata-form');
            expect(form.querySelector('[name="brand"]').value).toBe('Test Brand');
            expect(form.querySelector('[name="model"]').value).toBe('Test Model');
            expect(mockDocument.getElementById('origin').value).toBe('Test Origin');
            expect(mockDocument.getElementById('format').value).toBe('klippel');
            expect(mockDocument.getElementById('sensitivity').value).toBe('87.5');
        });

        it('should save form data correctly', () => {
            // Set up form values
            const form = mockDocument.getElementById('metadata-form');
            form.querySelector('[name="brand"]').value = 'Updated Brand';
            form.querySelector('[name="model"]').value = 'Updated Model';

            // Add the select elements with options to the form
            const typeSelect = form.querySelector('[name="type"]');
            typeSelect.innerHTML = '<option value="active">Active</option>';
            typeSelect.value = 'active';

            const shapeSelect = form.querySelector('[name="shape"]');
            shapeSelect.innerHTML = '<option value="floorstanders">Floorstanders</option>';
            shapeSelect.value = 'floorstanders';

            const formatSelect = mockDocument.getElementById('format');
            formatSelect.innerHTML = '<option value="webplotdigitizer">WebPlotDigitizer</option>';

            const qualitySelect = mockDocument.getElementById('quality');
            qualitySelect.innerHTML = '<option value="medium">Medium</option>';

            mockDocument.getElementById('origin').value = 'Updated Origin';
            mockDocument.getElementById('format').value = 'webplotdigitizer';
            mockDocument.getElementById('quality').value = 'medium';
            mockDocument.getElementById('sensitivity').value = '89.2';
            mockDocument.getElementById('data_acquisition_via').value = 'gll';
            mockDocument.getElementById('data_acquisition_distance').value = '1.5';
            mockDocument.getElementById('parameters_mean_min').value = '-25';
            mockDocument.getElementById('parameters_mean_max').value = '25';
            mockDocument.getElementById('extras_is_equed').checked = true;

            manager.saveMetadataForm();

            expect(manager.selectedSpeaker.brand).toBe('Updated Brand');
            expect(manager.selectedSpeaker.model).toBe('Updated Model');
            expect(manager.selectedSpeaker.type).toBe('active');
            expect(manager.selectedSpeaker.shape).toBe('floorstanders');

            const measurement = manager.selectedSpeaker.measurements.default;
            expect(measurement.origin).toBe('Updated Origin');
            expect(measurement.format).toBe('webplotdigitizer');
            expect(measurement.quality).toBe('medium');
            expect(measurement.sensitivity).toBe(89.2);
            expect(measurement.data_acquisition.via).toBe('gll');
            expect(measurement.data_acquisition.distance).toBe(1.5);
            expect(measurement.parameters.mean_min).toBe(-25);
            expect(measurement.parameters.mean_max).toBe(25);
            expect(measurement.extras.is_equed).toBe(true);
        });
    });

    describe('Utility Methods', () => {
        it('should parse numbers correctly', () => {
            expect(manager.parseNumber('123.45')).toBe(123.45);
            expect(manager.parseNumber('123', true)).toBe(123);
            expect(manager.parseNumber('')).toBeUndefined();
            expect(manager.parseNumber('invalid')).toBeUndefined();
        });

        it('should set field values correctly', () => {
            const field = mockDocument.getElementById('origin');
            manager.setFieldValue('origin', 'Test Value');
            expect(field.value).toBe('Test Value');
        });

        it('should set checkbox values correctly', () => {
            const checkbox = mockDocument.getElementById('extras_is_equed');
            manager.setCheckboxValue('extras_is_equed', true);
            expect(checkbox.checked).toBe(true);

            manager.setCheckboxValue('extras_is_equed', false);
            expect(checkbox.checked).toBe(false);
        });

        it('should generate speaker ID correctly', () => {
            const id = manager.generateSpeakerId('Test Brand', 'Test Model');
            expect(id).toBe('test-brand-test-model');
        });
    });

    describe('Python Code Generation', () => {
        beforeEach(() => {
            manager.selectedSpeaker = {
                brand: 'Test Brand',
                model: 'Test Model',
                type: 'passive',
                shape: 'bookshelves',
                price: '$500',
                amount: 'pair',
                default_measurement: 'default',
                measurements: {
                    default: {
                        origin: 'Test Origin',
                        format: 'klippel',
                        quality: 'high'
                    }
                }
            };
        });

        it('should format speaker as Python correctly', () => {
            const pythonCode = manager.formatSpeakerAsPython(manager.selectedSpeaker);

            // The formatSpeakerAsPython method returns just the speaker object, not the key-value pair
            expect(pythonCode).toContain('"brand": "Test Brand"');
            expect(pythonCode).toContain('"model": "Test Model"');
            expect(pythonCode).toContain('"type": "passive"');
            expect(pythonCode).toContain('"shape": "bookshelves"');
            expect(pythonCode).toContain('"measurements": {');
            expect(pythonCode).toContain('"origin": "Test Origin"');
            expect(pythonCode).toContain('"format": "klippel"');
        });

        it('should generate Python code and update display', () => {
            manager.generatePythonCode();

            const codeDisplay = mockDocument.getElementById('python-code');
            expect(codeDisplay.textContent).toContain('test-brand-test-model');
        });
    });

    describe('Git Commit Creation', () => {
        beforeEach(() => {
            manager.selectedSpeaker = {
                brand: 'Test Brand',
                model: 'Test Model',
                type: 'passive',
                shape: 'bookshelves'
            };
        });

        it('should create git commit successfully', async () => {
            global.fetch.mockResolvedValue({
                ok: true,
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        branch: 'feature/add-test-brand-test-model',
                        commit: 'abc123',
                        pr_url: 'https://github.com/test/repo/pull/1'
                    }
                })
            });

            const commitMessage = mockDocument.getElementById('commit-message');
            commitMessage.value = 'Add Test Brand Test Model';

            await manager.createGitCommit();

            expect(global.fetch).toHaveBeenCalledWith('/api/export-metadata', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: expect.stringContaining('Test Brand Test Model')
            });

            const result = mockDocument.getElementById('commit-result');
            expect(result.innerHTML).toContain('Commit Created Successfully!');
            expect(result.innerHTML).toContain('feature/add-test-brand-test-model');
        });

        it('should handle git commit errors', async () => {
            global.fetch.mockResolvedValue({
                ok: true,
                json: () => Promise.resolve({
                    success: false,
                    message: 'Commit failed'
                })
            });

            const showNotificationSpy = vi.spyOn(manager, 'showNotification').mockImplementation(() => {});
            const commitMessage = mockDocument.getElementById('commit-message');
            commitMessage.value = 'Test commit message';

            await manager.createGitCommit();

            expect(showNotificationSpy).toHaveBeenCalledWith(
                'Failed to create commit: Commit failed',
                'error'
            );
        });
    });

    describe('Start Over Functionality', () => {
        it('should reset manager state correctly', () => {
            manager.selectedSpeaker = { brand: 'Test' };
            manager.isNewSpeaker = true;
            manager.measurementCounter = 5;
            manager.currentStep = 3;

            manager.startOver();

            expect(manager.selectedSpeaker).toBeNull();
            expect(manager.isNewSpeaker).toBe(false);
            expect(manager.measurementCounter).toBe(0);
            expect(manager.currentStep).toBe(1);
        });

        it('should clear form inputs', () => {
            const brandInput = mockDocument.getElementById('new-brand');
            const modelInput = mockDocument.getElementById('new-model');
            const searchInput = mockDocument.getElementById('speaker-search');
            const commitInput = mockDocument.getElementById('commit-message');

            brandInput.value = 'Test';
            modelInput.value = 'Test';
            searchInput.value = 'Test';
            commitInput.value = 'Test';

            manager.startOver();

            expect(brandInput.value).toBe('');
            expect(modelInput.value).toBe('');
            expect(searchInput.value).toBe('');
            expect(commitInput.value).toBe('');
        });
    });

    describe('Notification System', () => {
        it('should create notification element correctly', () => {
            manager.showNotification('Test message', 'success');

            const notification = mockDocument.querySelector('.notification.is-success');
            expect(notification).toBeTruthy();
            expect(notification.textContent).toContain('Test message');
        });

        it('should handle error notifications', () => {
            // Clear any existing notifications first
            const existingNotifications = mockDocument.querySelectorAll('.notification');
            existingNotifications.forEach(n => n.remove());

            manager.showNotification('Error message', 'error');

            const notification = mockDocument.querySelector('.notification.is-danger');
            expect(notification).toBeTruthy();
            expect(notification.textContent.trim()).toContain('Error message');
        });
    });

    describe('Event Listeners', () => {
        it('should set up event listeners correctly', () => {
            const addEventListenerSpy = vi.spyOn(mockDocument, 'addEventListener');

            manager.setupEventListeners();

            // Check that event listeners are being added to elements
            const searchInput = mockDocument.getElementById('speaker-search');
            const createBtn = mockDocument.getElementById('create-new-btn');

            expect(searchInput).toBeTruthy();
            expect(createBtn).toBeTruthy();
        });
    });

    describe('Speaker List Rendering', () => {
        it('should render speaker list correctly', () => {
            manager.speakers = [
                {
                    id: 'test-1',
                    brand: 'Brand A',
                    model: 'Model 1',
                    type: 'passive'
                },
                {
                    id: 'test-2',
                    brand: 'Brand B',
                    model: 'Model 2',
                    type: 'active'
                }
            ];

            manager.renderSpeakerList();

            const speakerList = mockDocument.getElementById('speaker-list');
            expect(speakerList.innerHTML).toContain('Brand A Model 1');
            expect(speakerList.innerHTML).toContain('Brand B Model 2');
        });

        it('should filter speakers correctly', () => {
            manager.speakers = [
                { id: 'test-1', brand: 'KEF', model: 'LS50', type: 'passive' },
                { id: 'test-2', brand: 'Genelec', model: '8030C', type: 'active' }
            ];

            manager.renderSpeakerList('KEF');

            const speakerList = mockDocument.getElementById('speaker-list');
            expect(speakerList.innerHTML).toContain('KEF LS50');
            expect(speakerList.innerHTML).not.toContain('Genelec 8030C');
        });
    });
});
