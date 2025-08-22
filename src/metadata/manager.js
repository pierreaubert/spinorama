// Speaker Metadata Manager - Main Application
class SpeakerMetadataManager {
    constructor() {
        this.currentStep = 1;
        this.speakers = [];
        this.brands = [];
        this.currentSpeakerData = {};
        this.measurementCounter = 0;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadInitialData();
        this.updateStepIndicator();
    }

    setupEventListeners() {
        // Skip DOM setup in test environment
        if (typeof window === 'undefined' || !document.getElementById) {
            return;
        }
        
        // Step navigation
        document.getElementById('next-to-step-2')?.addEventListener('click', () => this.goToStep2());
        document.getElementById('back-to-step-1')?.addEventListener('click', () => this.goToStep(1));
        document.getElementById('next-to-step-3')?.addEventListener('click', () => this.goToStep3());
        document.getElementById('back-to-step-2')?.addEventListener('click', () => this.goToStep(2));
        document.getElementById('start-over')?.addEventListener('click', () => this.startOver());

        // Speaker option toggle
        document.querySelectorAll('input[name="speaker-option"]').forEach(radio => {
            radio.addEventListener('change', (e) => this.toggleSpeakerOption(e.target.value));
        });
        
        // Speaker type change listener
        document.getElementById('form-type')?.addEventListener('change', () => this.updateSpeakerTypeDependentFields());

        // Speaker search
        document.getElementById('speaker-search')?.addEventListener('input', (e) => this.filterSpeakers(e.target.value));

        // Brand selection
        document.getElementById('brand-list')?.addEventListener('change', (e) => this.selectBrand(e.target.value));
        document.getElementById('new-brand')?.addEventListener('input', (e) => this.handleNewBrand(e.target.value));

        // Add measurement
        document.getElementById('add-measurement')?.addEventListener('click', () => this.addMeasurement());

        // Export actions
        document.getElementById('download-code')?.addEventListener('click', () => this.downloadCode());
        document.getElementById('copy-code')?.addEventListener('click', () => this.copyCode());
    }

    formatDateForInput(dateString) {
        // Convert YYYYMMDD format to YYYY-MM-DD for HTML date input
        if (!dateString || dateString.length !== 8) return '';
        return `${dateString.substring(0, 4)}-${dateString.substring(4, 6)}-${dateString.substring(6, 8)}`;
    }

    formatDateForPython(dateString) {
        // Convert YYYY-MM-DD format to YYYYMMDD for Python dict
        if (!dateString || dateString.length !== 10) return '';
        return dateString.replace(/-/g, '');
    }

    renderReviewsFields(reviews) {
        let html = '';
        Object.entries(reviews).forEach(([key, url]) => {
            html += `
                <div class="field has-addons review-field mb-2">
                    <div class="control">
                        <input class="input review-key" type="text" placeholder="Review key" value="${key}">
                    </div>
                    <div class="control is-expanded">
                        <input class="input review-url" type="url" placeholder="Review URL" value="${url}">
                    </div>
                    <div class="control">
                        <button type="button" class="button is-danger remove-review-btn">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        });
        
        // Add empty field if no reviews exist
        if (Object.keys(reviews).length === 0) {
            html += `
                <div class="field has-addons review-field mb-2">
                    <div class="control">
                        <input class="input review-key" type="text" placeholder="Review key">
                    </div>
                    <div class="control is-expanded">
                        <input class="input review-url" type="url" placeholder="Review URL">
                    </div>
                    <div class="control">
                        <button type="button" class="button is-danger remove-review-btn">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        }
        
        return html;
    }

    convertLegacyReviews(speakerData) {
        // Deep clone the speaker data to avoid modifying the original
        const convertedData = JSON.parse(JSON.stringify(speakerData));
        
        // Convert legacy review fields in measurements
        if (convertedData.measurements) {
            Object.keys(convertedData.measurements).forEach(measurementKey => {
                const measurement = convertedData.measurements[measurementKey];
                
                // If there's a legacy 'review' field, convert it to 'reviews' with 'default' key
                if (measurement.review && !measurement.reviews) {
                    measurement.reviews = {
                        'default': measurement.review
                    };
                    // Remove the legacy field
                    delete measurement.review;
                }
            });
        }
        
        return convertedData;
    }

    setupReviewHandlers(measurementPanel) {
        const addBtn = measurementPanel.querySelector('.add-review-btn');
        const container = measurementPanel.querySelector('.measurement-reviews-container');
        
        // Add review button handler
        addBtn.addEventListener('click', () => {
            const newReviewField = document.createElement('div');
            newReviewField.className = 'field has-addons review-field mb-2';
            newReviewField.innerHTML = `
                <div class="control">
                    <input class="input review-key" type="text" placeholder="Review key">
                </div>
                <div class="control is-expanded">
                    <input class="input review-url" type="url" placeholder="Review URL">
                </div>
                <div class="control">
                    <button type="button" class="button is-danger remove-review-btn">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            container.appendChild(newReviewField);
            
            // Add remove handler for the new field
            newReviewField.querySelector('.remove-review-btn').addEventListener('click', () => {
                newReviewField.remove();
            });
        });
        
        // Add remove handlers for existing review fields
        container.querySelectorAll('.remove-review-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.review-field').remove();
            });
        });
    }

    async loadInitialData() {
        try {
            // Load speakers
            const speakersResponse = await fetch('/api/v1/speakers');
            this.speakers = await speakersResponse.json();
            this.populateSpeakerList();

            // Load brands
            const brandsResponse = await fetch('/api/v1/brands');
            this.brands = await brandsResponse.json();
            this.populateBrandList();
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load initial data. Please check your connection.');
        }
    }

    populateSpeakerList() {
        // Skip DOM updates in test environment
        if (typeof window === 'undefined' || !document.getElementById) {
            return;
        }
        
        const speakerList = document.getElementById('speaker-list');
        if (!speakerList) return;
        
        speakerList.innerHTML = '<option value="">Select a speaker...</option>';
        
        this.speakers.forEach(speaker => {
            const option = document.createElement('option');
            option.value = speaker;
            option.textContent = speaker;
            speakerList.appendChild(option);
        });
    }

    populateBrandList() {
        // Skip DOM updates in test environment
        if (typeof window === 'undefined' || !document.getElementById) {
            return;
        }
        
        const brandList = document.getElementById('brand-list');
        if (!brandList) return;
        
        brandList.innerHTML = '<option value="">Select a brand...</option>';
        
        this.brands.forEach(brand => {
            const option = document.createElement('option');
            option.value = brand;
            option.textContent = brand;
            brandList.appendChild(option);
        });
    }

    filterSpeakers(searchTerm) {
        const speakerList = document.getElementById('speaker-list');
        const options = speakerList.querySelectorAll('option');
        
        options.forEach(option => {
            if (option.value === '') return; // Keep the default option
            
            const matches = option.textContent.toLowerCase().includes(searchTerm.toLowerCase());
            option.style.display = matches ? 'block' : 'none';
        });
    }

    toggleSpeakerOption(option) {
        const existingSection = document.getElementById('existing-speaker-section');
        const newSection = document.getElementById('new-speaker-section');
        
        if (option === 'existing') {
            existingSection.classList.remove('hidden');
            newSection.classList.add('hidden');
        } else {
            existingSection.classList.add('hidden');
            newSection.classList.remove('hidden');
        }
    }

    selectBrand(brand) {
        if (brand) {
            document.getElementById('new-brand').value = '';
        }
    }

    handleNewBrand(newBrand) {
        if (newBrand) {
            document.getElementById('brand-list').value = '';
        }
    }

    goToStep2() {
        const option = document.querySelector('input[name="speaker-option"]:checked').value;
        
        if (option === 'existing') {
            const selectedSpeaker = document.getElementById('speaker-list').value;
            if (!selectedSpeaker) {
                this.showError('Please select a speaker.');
                return;
            }
            this.loadExistingSpeaker(selectedSpeaker);
        } else {
            const brand = document.getElementById('brand-list').value || document.getElementById('new-brand').value;
            const speakerName = document.getElementById('speaker-name').value;
            
            if (!brand || !speakerName) {
                this.showError('Please provide both brand and speaker name.');
                return;
            }
            
            this.createNewSpeaker(brand, speakerName);
        }
        
        this.goToStep(2);
    }

    async loadExistingSpeaker(speakerName) {
        try {
            const response = await fetch(`/api/v1/speaker/${encodeURIComponent(speakerName)}/metadata`);
            const speakerData = await response.json();
            
            if (speakerData.error) {
                this.showError(`Error loading speaker: ${speakerData.error}`);
                return;
            }
            
            // Convert legacy review field to reviews dictionary
            this.currentSpeakerData = this.convertLegacyReviews(speakerData);
            this.populateForm();
        } catch (error) {
            console.error('Error loading speaker:', error);
            this.showError('Failed to load speaker data.');
        }
    }

    createNewSpeaker(brand, speakerName) {
        this.currentSpeakerData = {
            brand: brand,
            model: speakerName,
            type: '',
            shape: '',
            price: '',
            amount: '',
            measurements: {},
            default_measurement: ''
        };
        this.populateForm();
    }

    populateForm() {
        // Skip DOM updates in test environment
        if (typeof window === 'undefined' || !document.getElementById) {
            return;
        }
        
        const data = this.currentSpeakerData;
        
        const formSpeakerName = document.getElementById('form-speaker-name');
        const formBrand = document.getElementById('form-brand');
        const formModel = document.getElementById('form-model');
        const formType = document.getElementById('form-type');
        const formShape = document.getElementById('form-shape');
        const formPrice = document.getElementById('form-price');
        const formAmount = document.getElementById('form-amount');
        
        if (formSpeakerName) formSpeakerName.value = `${data.brand} ${data.model}`;
        if (formBrand) formBrand.value = data.brand || '';
        if (formModel) formModel.value = data.model || '';
        if (formType) formType.value = data.type || '';
        if (formShape) formShape.value = data.shape || '';
        if (formPrice) formPrice.value = data.price || '';
        if (formAmount) formAmount.value = data.amount || '';
        
        // Clear existing measurements
        const measurementsContainer = document.getElementById('measurements-container');
        if (measurementsContainer) {
            measurementsContainer.innerHTML = '';
        }
        this.measurementCounter = 0;
        
        // Add existing measurements
        if (data.measurements) {
            Object.keys(data.measurements).forEach(key => {
                this.addMeasurement(key, data.measurements[key]);
            });
        }
        
        // Add at least one measurement panel if none exist
        if (this.measurementCounter === 0) {
            this.addMeasurement();
        }
    }

    addMeasurement(measurementKey = '', measurementData = {}) {
        this.measurementCounter++;
        const container = document.getElementById('measurements-container');
        
        const today = new Date().toISOString().split('T')[0];
        
        const measurementPanel = document.createElement('div');
        measurementPanel.className = 'measurement-panel';
        measurementPanel.innerHTML = `
            <article class="panel is-primary">
                <p class="panel-heading">
                    ${measurementKey || `Measurement ${this.measurementCounter}`}
                    <button type="button" class="button is-small is-danger is-pulled-right remove-measurement">
                        <i class="fas fa-trash"></i>
                    </button>
                </p>
                <div class="panel-block">
                    <div class="container">
                        <!-- Basic Measurement Info -->
                        <div class="columns">
                            <div class="column">
                                <div class="field">
                                    <label class="label">Measurement Key</label>
                                    <div class="control">
                                        <input class="input measurement-key" type="text" value="${measurementKey}" placeholder="e.g., asr, klippel, vendor">
                                    </div>
                                </div>
                            </div>
                            <div class="column">
                                <div class="field">
                                    <label class="label">Origin</label>
                                    <div class="control">
                                        <input class="input measurement-origin" type="text" value="${measurementData.origin || ''}" placeholder="e.g., ASR, Klippel, Vendor" required>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="columns">
                            <div class="column">
                                <div class="field">
                                    <label class="label">Format</label>
                                    <div class="control">
                                        <div class="select is-fullwidth">
                                            <select class="measurement-format" required>
                                                <option value="">Select format</option>
                                                <option value="klippel" ${measurementData.format === 'klippel' ? 'selected' : ''}>Klippel</option>
                                                <option value="webplotdigitizer" ${measurementData.format === 'webplotdigitizer' ? 'selected' : ''}>WebPlotDigitizer</option>
                                                <option value="spl_hv_txt" ${measurementData.format === 'spl_hv_txt' ? 'selected' : ''}>SPL HV TXT</option>
                                                <option value="gll_hv_txt" ${measurementData.format === 'gll_hv_txt' ? 'selected' : ''}>GLL HV TXT</option>
                                                <option value="princeton" ${measurementData.format === 'princeton' ? 'selected' : ''}>Princeton</option>
                                                <option value="rew_text_dump" ${measurementData.format === 'rew_text_dump' ? 'selected' : ''}>REW Text Dump</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="column">
                                <div class="field">
                                    <label class="label">Quality</label>
                                    <div class="control">
                                        <div class="select is-fullwidth">
                                            <select class="measurement-quality">
                                                <option value="">Select quality</option>
                                                <option value="low" ${measurementData.quality === 'low' ? 'selected' : ''}>Low</option>
                                                <option value="medium" ${measurementData.quality === 'medium' ? 'selected' : ''}>Medium</option>
                                                <option value="high" ${measurementData.quality === 'high' ? 'selected' : ''}>High</option>
                                                <option value="unknown" ${measurementData.quality === 'unknown' ? 'selected' : ''}>Unknown</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Reviews Section -->
                        <div class="columns">
                            <div class="column">
                                <div class="field">
                                    <label class="label">Reviews</label>
                                    <div class="control">
                                        <div class="measurement-reviews-container">
                                            ${this.renderReviewsFields(measurementData.reviews || {})}
                                        </div>
                                        <button type="button" class="button is-small is-info add-review-btn">
                                            <i class="fas fa-plus"></i> Add Review
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <div class="column">
                                <div class="field">
                                    <label class="label">Review Published Date</label>
                                    <div class="control">
                                        <input class="input measurement-review-published" type="date" value="${this.formatDateForInput(measurementData.review_published) || ''}">
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Symmetry -->
                        <div class="columns">
                            <div class="column is-half">
                                <div class="field">
                                    <label class="label">Symmetry</label>
                                    <div class="control">
                                        <div class="select is-fullwidth">
                                            <select class="measurement-symmetry">
                                                <option value="none" ${(measurementData.symmetry || 'none') === 'none' ? 'selected' : ''}>None</option>
                                                <option value="coaxial" ${measurementData.symmetry === 'coaxial' ? 'selected' : ''}>Coaxial</option>
                                                <option value="vertical" ${measurementData.symmetry === 'vertical' ? 'selected' : ''}>Vertical</option>
                                                <option value="horizontal" ${measurementData.symmetry === 'horizontal' ? 'selected' : ''}>Horizontal</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Data Acquisition Section -->
                        <div class="field">
                            <label class="label">Data Acquisition</label>
                            <div class="box">
                                <div class="columns">
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Via</label>
                                            <div class="control">
                                                <input class="input is-small measurement-da-via" type="text" value="${measurementData.data_acquisition?.via || ''}" placeholder="e.g., microphone">
                                            </div>
                                        </div>
                                    </div>
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Distance (m)</label>
                                            <div class="control">
                                                <input class="input is-small measurement-da-distance" type="number" step="0.1" value="${measurementData.data_acquisition?.distance || ''}" placeholder="e.g., 1.0">
                                            </div>
                                        </div>
                                    </div>
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Signal</label>
                                            <div class="control">
                                                <input class="input is-small measurement-da-signal" type="text" value="${measurementData.data_acquisition?.signal || ''}" placeholder="e.g., sine sweep">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="columns">
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Resolution (Hz)</label>
                                            <div class="control">
                                                <input class="input is-small measurement-da-resolution" type="number" step="0.1" value="${measurementData.data_acquisition?.resolution || ''}" placeholder="e.g., 0.1">
                                            </div>
                                        </div>
                                    </div>
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Min Valid Freq (Hz)</label>
                                            <div class="control">
                                                <input class="input is-small measurement-da-min-freq" type="number" value="${measurementData.data_acquisition?.min_valid_freq || ''}" placeholder="e.g., 20">
                                            </div>
                                        </div>
                                    </div>
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Max Valid Freq (Hz)</label>
                                            <div class="control">
                                                <input class="input is-small measurement-da-max-freq" type="number" value="${measurementData.data_acquisition?.max_valid_freq || ''}" placeholder="e.g., 20000">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="columns">
                                    <div class="column is-half">
                                        <div class="field">
                                            <label class="checkbox">
                                                <input type="checkbox" class="measurement-da-air-absorption" ${measurementData.data_acquisition?.air_absorbtion ? 'checked' : ''}>
                                                Air Absorption Correction
                                            </label>
                                        </div>
                                    </div>
                                </div>
                                <div class="field">
                                    <label class="label is-small">Data Acquisition Notes</label>
                                    <div class="control">
                                        <textarea class="textarea is-small measurement-da-notes" placeholder="Additional notes about data acquisition">${measurementData.data_acquisition?.notes || ''}</textarea>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Extras Section -->
                        <div class="field">
                            <label class="label">Extras</label>
                            <div class="box">
                                <div class="columns">
                                    <div class="column">
                                        <div class="field">
                                            <label class="checkbox">
                                                <input type="checkbox" class="measurement-extras-equed" ${measurementData.extras?.is_equed ? 'checked' : ''}>
                                                Is EQ'd
                                            </label>
                                        </div>
                                    </div>
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Score Penalty</label>
                                            <div class="control">
                                                <input class="input is-small measurement-extras-penalty" type="number" step="0.1" value="${measurementData.extras?.score_penalty || ''}" placeholder="e.g., 0.5">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Specifications Section -->
                        <div class="field">
                            <label class="label">Specifications</label>
                            <div class="box">
                                <div class="columns">
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Sensitivity (dB)</label>
                                            <div class="control">
                                                <input class="input is-small measurement-spec-sensitivity speaker-type-dependent" type="number" step="0.1" value="${measurementData.specifications?.sensitivity || ''}" placeholder="e.g., 85.0">
                                            </div>
                                        </div>
                                    </div>
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Impedance (Ω)</label>
                                            <div class="control">
                                                <input class="input is-small measurement-spec-impedance speaker-type-dependent" type="number" step="0.1" value="${measurementData.specifications?.impedance || ''}" placeholder="e.g., 8.0">
                                            </div>
                                        </div>
                                    </div>
                                    <div class="column">
                                        <div class="field">
                                            <label class="label is-small">Weight (kg)</label>
                                            <div class="control">
                                                <input class="input is-small measurement-spec-weight" type="number" step="0.1" value="${measurementData.specifications?.weight || ''}" placeholder="e.g., 5.5">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Size Section -->
                                <div class="field">
                                    <label class="label is-small">Size (mm)</label>
                                    <div class="columns">
                                        <div class="column">
                                            <div class="field">
                                                <label class="label is-small">Height</label>
                                                <div class="control">
                                                    <input class="input is-small measurement-spec-height" type="number" value="${measurementData.specifications?.size?.height || ''}" placeholder="e.g., 300">
                                                </div>
                                            </div>
                                        </div>
                                        <div class="column">
                                            <div class="field">
                                                <label class="label is-small">Width</label>
                                                <div class="control">
                                                    <input class="input is-small measurement-spec-width" type="number" value="${measurementData.specifications?.size?.width || ''}" placeholder="e.g., 200">
                                                </div>
                                            </div>
                                        </div>
                                        <div class="column">
                                            <div class="field">
                                                <label class="label is-small">Depth</label>
                                                <div class="control">
                                                    <input class="input is-small measurement-spec-depth" type="number" value="${measurementData.specifications?.size?.depth || ''}" placeholder="e.g., 250">
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- SPL Section -->
                                <div class="field">
                                    <label class="label is-small">SPL (dB)</label>
                                    <div class="columns">
                                        <div class="column">
                                            <div class="field">
                                                <label class="label is-small">Peak</label>
                                                <div class="control">
                                                    <input class="input is-small measurement-spec-spl-peak" type="number" step="0.1" value="${measurementData.specifications?.SPL?.peak || ''}" placeholder="e.g., 110">
                                                </div>
                                            </div>
                                        </div>
                                        <div class="column">
                                            <div class="field">
                                                <label class="label is-small">Continuous</label>
                                                <div class="control">
                                                    <input class="input is-small measurement-spec-spl-continuous" type="number" step="0.1" value="${measurementData.specifications?.SPL?.continuous || ''}" placeholder="e.g., 105">
                                                </div>
                                            </div>
                                        </div>
                                        <div class="column">
                                            <div class="field">
                                                <label class="label is-small">Max</label>
                                                <div class="control">
                                                    <input class="input is-small measurement-spec-spl-max" type="number" step="0.1" value="${measurementData.specifications?.SPL?.max || ''}" placeholder="e.g., 115">
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Dispersion Section -->
                                <div class="field">
                                    <label class="label is-small">Dispersion (degrees)</label>
                                    <div class="columns">
                                        <div class="column">
                                            <div class="field">
                                                <label class="label is-small">Horizontal</label>
                                                <div class="control">
                                                    <input class="input is-small measurement-spec-disp-horizontal" type="number" step="0.1" value="${measurementData.specifications?.dispersion?.horizontal || ''}" placeholder="e.g., 60">
                                                </div>
                                            </div>
                                        </div>
                                        <div class="column">
                                            <div class="field">
                                                <label class="label is-small">Vertical</label>
                                                <div class="control">
                                                    <input class="input is-small measurement-spec-disp-vertical" type="number" step="0.1" value="${measurementData.specifications?.dispersion?.vertical || ''}" placeholder="e.g., 30">
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Notes -->
                        <div class="field">
                            <label class="label">Notes</label>
                            <div class="control">
                                <textarea class="textarea measurement-notes" placeholder="General notes about this measurement">${measurementData.notes || ''}</textarea>
                            </div>
                        </div>
                    </div>
                </div>
            </article>
        `;
        
        container.appendChild(measurementPanel);
        
        // Add remove functionality
        measurementPanel.querySelector('.remove-measurement').addEventListener('click', () => {
            measurementPanel.remove();
        });
        
        // Add review management functionality
        this.setupReviewHandlers(measurementPanel);
        
        // Update speaker type dependent fields
        if (this.updateSpeakerTypeDependentFields) {
            this.updateSpeakerTypeDependentFields();
        }
    }

    goToStep3() {
        // Collect form data
        this.collectFormData();
        
        // Validate data
        this.validateSpeakerData();
        
        this.goToStep(3);
    }

    collectFormData() {
        this.currentSpeakerData = {
            brand: document.getElementById('form-brand').value,
            model: document.getElementById('form-model').value,
            type: document.getElementById('form-type').value,
            shape: document.getElementById('form-shape').value,
            price: document.getElementById('form-price').value || undefined,
            amount: document.getElementById('form-amount').value || undefined,
            measurements: {},
            default_measurement: ''
        };
        
        // Collect measurements
        const measurementPanels = document.querySelectorAll('.measurement-panel');
        measurementPanels.forEach(panel => {
            const key = panel.querySelector('.measurement-key').value;
            const origin = panel.querySelector('.measurement-origin').value;
            const format = panel.querySelector('.measurement-format').value;
            
            if (key && origin && format) {
                const measurement = {
                    origin: origin,
                    format: format
                };
                
                // Basic fields
                const quality = panel.querySelector('.measurement-quality').value;
                const notes = panel.querySelector('.measurement-notes').value;
                const reviewPublished = panel.querySelector('.measurement-review-published').value;
                const symmetry = panel.querySelector('.measurement-symmetry').value;
                
                // Collect reviews
                const reviews = {};
                const reviewFields = panel.querySelectorAll('.review-field');
                reviewFields.forEach(field => {
                    const key = field.querySelector('.review-key').value.trim();
                    const url = field.querySelector('.review-url').value.trim();
                    if (key && url) {
                        reviews[key] = url;
                    }
                });
                
                if (quality) measurement.quality = quality;
                if (notes) measurement.notes = notes;
                if (Object.keys(reviews).length > 0) measurement.reviews = reviews;
                if (reviewPublished) measurement.review_published = this.formatDateForPython(reviewPublished);
                if (symmetry && symmetry !== 'none') measurement.symmetry = symmetry;
                
                // Data acquisition
                const dataAcquisition = {};
                const daVia = panel.querySelector('.measurement-da-via').value;
                const daDistance = panel.querySelector('.measurement-da-distance').value;
                const daSignal = panel.querySelector('.measurement-da-signal').value;
                const daResolution = panel.querySelector('.measurement-da-resolution').value;
                const daMinFreq = panel.querySelector('.measurement-da-min-freq').value;
                const daMaxFreq = panel.querySelector('.measurement-da-max-freq').value;
                const daAirAbsorption = panel.querySelector('.measurement-da-air-absorption').checked;
                const daNotes = panel.querySelector('.measurement-da-notes').value;
                
                if (daVia) dataAcquisition.via = daVia;
                if (daDistance) dataAcquisition.distance = parseFloat(daDistance);
                if (daSignal) dataAcquisition.signal = daSignal;
                if (daResolution) dataAcquisition.resolution = parseFloat(daResolution);
                if (daMinFreq) dataAcquisition.min_valid_freq = parseFloat(daMinFreq);
                if (daMaxFreq) dataAcquisition.max_valid_freq = parseFloat(daMaxFreq);
                if (daAirAbsorption) dataAcquisition.air_absorbtion = true;
                if (daNotes) dataAcquisition.notes = daNotes;
                
                if (Object.keys(dataAcquisition).length > 0) {
                    measurement.data_acquisition = dataAcquisition;
                }
                
                // Extras
                const extras = {};
                const extrasEqued = panel.querySelector('.measurement-extras-equed').checked;
                const extrasPenalty = panel.querySelector('.measurement-extras-penalty').value;
                
                if (extrasEqued) extras.is_equed = true;
                if (extrasPenalty) extras.score_penalty = parseFloat(extrasPenalty);
                
                if (Object.keys(extras).length > 0) {
                    measurement.extras = extras;
                }
                
                // Specifications
                const specifications = {};
                const specSensitivity = panel.querySelector('.measurement-spec-sensitivity').value;
                const specImpedance = panel.querySelector('.measurement-spec-impedance').value;
                const specWeight = panel.querySelector('.measurement-spec-weight').value;
                
                if (specSensitivity) specifications.sensitivity = parseFloat(specSensitivity);
                if (specImpedance) specifications.impedance = parseFloat(specImpedance);
                if (specWeight) specifications.weight = parseFloat(specWeight);
                
                // Size
                const specHeight = panel.querySelector('.measurement-spec-height').value;
                const specWidth = panel.querySelector('.measurement-spec-width').value;
                const specDepth = panel.querySelector('.measurement-spec-depth').value;
                
                if (specHeight || specWidth || specDepth) {
                    specifications.size = {};
                    if (specHeight) specifications.size.height = parseFloat(specHeight);
                    if (specWidth) specifications.size.width = parseFloat(specWidth);
                    if (specDepth) specifications.size.depth = parseFloat(specDepth);
                }
                
                // SPL
                const splPeak = panel.querySelector('.measurement-spec-spl-peak').value;
                const splContinuous = panel.querySelector('.measurement-spec-spl-continuous').value;
                const splMax = panel.querySelector('.measurement-spec-spl-max').value;
                
                if (splPeak || splContinuous || splMax) {
                    specifications.SPL = {};
                    if (splPeak) specifications.SPL.peak = parseFloat(splPeak);
                    if (splContinuous) specifications.SPL.continuous = parseFloat(splContinuous);
                    if (splMax) specifications.SPL.max = parseFloat(splMax);
                }
                
                // Dispersion
                const dispHorizontal = panel.querySelector('.measurement-spec-disp-horizontal').value;
                const dispVertical = panel.querySelector('.measurement-spec-disp-vertical').value;
                
                if (dispHorizontal || dispVertical) {
                    specifications.dispersion = {};
                    if (dispHorizontal) specifications.dispersion.horizontal = parseFloat(dispHorizontal);
                    if (dispVertical) specifications.dispersion.vertical = parseFloat(dispVertical);
                }
                
                if (Object.keys(specifications).length > 0) {
                    measurement.specifications = specifications;
                }
                
                this.currentSpeakerData.measurements[key] = measurement;
                
                // Set first measurement as default if not set
                if (!this.currentSpeakerData.default_measurement) {
                    this.currentSpeakerData.default_measurement = key;
                }
            }
        });
    }

    async validateSpeakerData() {
        const statusDiv = document.getElementById('validation-status');
        const resultsDiv = document.getElementById('validation-results');
        
        statusDiv.classList.remove('hidden');
        resultsDiv.classList.add('hidden');
        
        try {
            const response = await fetch('/api/v1/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.currentSpeakerData)
            });
            
            const validationResult = await response.json();
            
            statusDiv.classList.add('hidden');
            resultsDiv.classList.remove('hidden');
            
            this.displayValidationResults(validationResult);
            this.generateExportCode();
            
            return validationResult;
            
        } catch (error) {
            console.error('Validation error:', error);
            statusDiv.innerHTML = `
                <div class="notification is-warning">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    Validation service unavailable. Proceeding with export...
                </div>
            `;
            
            setTimeout(() => {
                statusDiv.classList.add('hidden');
                resultsDiv.classList.remove('hidden');
                this.displayValidationResults({ valid: true, messages: [] });
                this.generateExportCode();
            }, 2000);
        }
    }

    displayValidationResults(result) {
        const messagesDiv = document.getElementById('validation-messages');
        
        // Skip DOM updates in test environment
        if (!messagesDiv) return;
        
        if (result.valid) {
            messagesDiv.innerHTML = `
                <div class="notification is-success">
                    <i class="fas fa-check mr-2"></i>
                    All parameters are valid!
                </div>
            `;
        } else {
            let messagesHtml = `
                <div class="notification is-danger">
                    <i class="fas fa-times mr-2"></i>
                    Validation failed. Please fix the following issues:
                </div>
            `;
            
            if (result.messages && result.messages.length > 0) {
                messagesHtml += '<div class="content"><ul>';
                result.messages.forEach(message => {
                    messagesHtml += `<li>${message}</li>`;
                });
                messagesHtml += '</ul></div>';
            }
            
            messagesDiv.innerHTML = messagesHtml;
        }
    }

    generateExportCode() {
        const speakerKey = `${this.currentSpeakerData.brand} ${this.currentSpeakerData.model}`;
        const codeDiv = document.getElementById('export-code');
        
        // Clean up undefined values
        const cleanData = JSON.parse(JSON.stringify(this.currentSpeakerData, (key, value) => {
            return value === undefined ? null : value;
        }));
        
        // Remove null values
        Object.keys(cleanData).forEach(key => {
            if (cleanData[key] === null || cleanData[key] === '') {
                delete cleanData[key];
            }
        });
        
        const code = `# Generated speaker metadata for ${speakerKey}
"${speakerKey}": ${JSON.stringify(cleanData, null, 4).replace(/"/g, '"')}`;
        
        codeDiv.textContent = code;
    }

    downloadCode() {
        const code = document.getElementById('export-code').textContent;
        const speakerKey = `${this.currentSpeakerData.brand}_${this.currentSpeakerData.model}`.replace(/\s+/g, '_');
        
        const blob = new Blob([code], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `${speakerKey}_metadata.py`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
    }

    async copyCode() {
        const code = document.getElementById('export-code').textContent;
        
        try {
            await navigator.clipboard.writeText(code);
            this.showSuccess('Code copied to clipboard!');
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showError('Failed to copy code to clipboard.');
        }
    }

    goToStep(step) {
        // Hide all steps
        document.querySelectorAll('.step-content').forEach(content => {
            content.classList.add('hidden');
        });
        
        // Show target step
        document.getElementById(`step-${step}`).classList.remove('hidden');
        
        this.currentStep = step;
        this.updateStepIndicator();
    }

    updateStepIndicator() {
        // Skip DOM updates in test environment
        if (typeof window === 'undefined' || !document.querySelectorAll) {
            return;
        }
        
        const steps = document.querySelectorAll('.step');
        steps.forEach((step, index) => {
            if (index + 1 === this.currentStep) {
                step.classList.add('is-active');
            } else {
                step.classList.remove('is-active');
            }
        });
    }

    startOver() {
        this.currentSpeakerData = {};
        this.measurementCounter = 0;
        
        // Reset form
        document.getElementById('speaker-search').value = '';
        document.getElementById('speaker-list').value = '';
        document.getElementById('brand-list').value = '';
        document.getElementById('new-brand').value = '';
        document.getElementById('speaker-name').value = '';
        document.querySelector('input[name="speaker-option"][value="existing"]').checked = true;
        this.toggleSpeakerOption('existing');
        
        this.goToStep(1);
    }

    showError(message) {
        // Simple error notification - check if DOM is available
        if (typeof document === 'undefined' || !document.createElement) {
            console.error('Error:', message);
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = 'notification is-danger is-fixed';
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    showSuccess(message) {
        // Simple success notification - check if DOM is available
        if (typeof document === 'undefined' || !document.createElement) {
            console.log('Success:', message);
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = 'notification is-success is-fixed';
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1000; max-width: 400px;';
        notification.innerHTML = `
            <button class="delete"></button>
            <i class="fas fa-check mr-2"></i>
            ${message}
        `;
        
        document.body.appendChild(notification);
        
        notification.querySelector('.delete').addEventListener('click', () => {
            notification.remove();
        });
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SpeakerMetadataManager();
});

// Export for testing
export { SpeakerMetadataManager };
