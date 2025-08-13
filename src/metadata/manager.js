// Simple 3-Step Speaker Metadata Manager
class SimpleMetadataManager {
    constructor() {
        this.currentStep = 1;
        this.selectedSpeaker = null;
        this.isNewSpeaker = false;
        this.speakers = [];
        this.measurementCounter = 0;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadSpeakers();
        this.showStep(1);
    }
    
    showStep(stepNum) {
        this.currentStep = stepNum;
        
        // Update step indicators
        ['step-1-indicator', 'step-2-indicator', 'step-3-indicator'].forEach((id, idx) => {
            const el = document.getElementById(id);
            if (!el) return;
            if (idx < stepNum - 1) {
                el.classList.add('is-completed');
                el.classList.remove('is-active');
            } else if (idx === stepNum - 1) {
                el.classList.add('is-active');
                el.classList.remove('is-completed');
            } else {
                el.classList.remove('is-active', 'is-completed');
            }
        });
        
        // Show/hide step content
        ['step-1', 'step-2', 'step-3'].forEach((id, idx) => {
            const el = document.getElementById(id);
            if (!el) return;
            if (idx === stepNum - 1) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        });
        
        // Manage step navigation buttons
        const continueStep2 = document.getElementById('continue-step-2');
        if (continueStep2) {
            // Disable Step 3 button when at Step 1
            continueStep2.disabled = (stepNum === 1);
        }
        
        // Special handling for each step
        if (stepNum === 3) {
            this.generatePythonCode();
        }
    }
    
    setupEventListeners() {
        // Step 1: Speaker search
        const searchInput = document.getElementById('speaker-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterSpeakers(e.target.value);
            });
        }
        
        // Step 1: Create new speaker button
        const createNewBtn = document.getElementById('create-new-btn');
        if (createNewBtn) {
            createNewBtn.addEventListener('click', () => {
                this.createNewSpeaker();
            });
        }
        
        // Step 1: Continue button
        const continueStep1 = document.getElementById('continue-step-1');
        if (continueStep1) {
            continueStep1.addEventListener('click', () => {
                this.showStep(2);
                this.populateMetadataForm();
            });
        }
        
        // Step 2: Add measurement button
        const addMeasurementBtn = document.getElementById('add-measurement-btn');
        if (addMeasurementBtn) {
            addMeasurementBtn.addEventListener('click', () => {
                this.addMeasurement();
            });
        }
        
        // Step 2: Measurement tab switching
        this.setupMeasurementTabListeners();
        
        // Step 2: Back and continue buttons
        const backStep1 = document.getElementById('back-step-1');
        if (backStep1) {
            backStep1.addEventListener('click', () => {
                this.showStep(1);
            });
        }
        
        const continueStep2 = document.getElementById('continue-step-2');
        if (continueStep2) {
            continueStep2.addEventListener('click', () => {
                this.saveMetadataForm();
                this.showStep(3);
            });
        }
        
        // Speaker type change listener
        const speakerTypeSelect = document.querySelector('[name="type"]');
        if (speakerTypeSelect) {
            speakerTypeSelect.addEventListener('change', () => {
                this.handleSpeakerTypeChange();
            });
        }
        
        // Step 3: Back and commit buttons
        const backStep2 = document.getElementById('back-step-2');
        if (backStep2) {
            backStep2.addEventListener('click', () => {
                this.showStep(2);
            });
        }

        const writeMetadataBtn = document.getElementById('write-metadata-btn');
        if (writeMetadataBtn) {
            writeMetadataBtn.addEventListener('click', () => {
                this.writeMetadataToFile();
            });
        }

        const createCommitBtn = document.getElementById('create-commit-btn');
        if (createCommitBtn) {
            createCommitBtn.addEventListener('click', () => {
                this.createGitCommit();
            });
        }

        const startOverBtn = document.getElementById('start-over-btn');
        if (startOverBtn) {
            startOverBtn.addEventListener('click', () => {
                this.startOver();
            });
        }
    }
    
    async loadSpeakers() {
        try {
            const response = await fetch('/api/speakers');
            const result = await response.json();
            
            if (result.success) {
                this.speakers = result.data;
                this.renderSpeakerList();
            } else {
                throw new Error(result.message || 'Failed to load speakers');
            }
        } catch (error) {
            console.error('Failed to load speakers:', error);
            this.showNotification('Failed to load speakers', 'error');
            // Show fallback message
            const speakerList = document.getElementById('speaker-list');
            if (speakerList) {
                speakerList.innerHTML = '<div class="has-text-centered has-text-grey"><p>Failed to load speakers. Please refresh the page.</p></div>';
            }
        }
    }
    
    renderSpeakerList(filter = '') {
        const speakerList = document.getElementById('speaker-list');
        if (!speakerList) return;
        
        const filteredSpeakers = this.speakers.filter(speaker => {
            if (!filter) return true;
            const searchText = `${speaker.brand} ${speaker.model}`.toLowerCase();
            return searchText.includes(filter.toLowerCase());
        });
        
        if (filteredSpeakers.length === 0) {
            speakerList.innerHTML = '<div class="has-text-centered has-text-grey"><p>No speakers found</p></div>';
            return;
        }
        
        speakerList.innerHTML = filteredSpeakers.map(speaker => `
            <div class="speaker-item" data-speaker-id="${speaker.id}">
                <div class="has-text-weight-semibold">${speaker.brand} ${speaker.model}</div>
                <div class="is-size-7 has-text-grey">${speaker.type} • ${speaker.shape}</div>
                <div class="is-size-7 has-text-grey">${Object.keys(speaker.measurements || {}).length} measurements</div>
            </div>
        `).join('');
        
        // Add click handlers
        speakerList.querySelectorAll('.speaker-item').forEach(item => {
            item.addEventListener('click', () => {
                const speakerId = item.dataset.speakerId;
                const speaker = this.speakers.find(s => s.id === speakerId);
                this.selectSpeaker(speaker, item);
            });
        });
    }
    
    filterSpeakers(filter) {
        this.renderSpeakerList(filter);
    }
    
    selectSpeaker(speaker, element) {
        this.selectedSpeaker = speaker;
        this.isNewSpeaker = false;
        
        // Update UI to show selection
        document.querySelectorAll('.speaker-item').forEach(item => {
            item.classList.remove('selected');
        });
        element.classList.add('selected');
        
        // Enable continue button
        const continueBtn = document.getElementById('continue-step-1');
        if (continueBtn) {
            continueBtn.disabled = false;
        }
    }
    
    createNewSpeaker() {
        const brand = document.getElementById('new-brand').value.trim();
        const model = document.getElementById('new-model').value.trim();
        
        if (!brand || !model) {
            this.showNotification('Please enter both brand and model', 'error');
            return;
        }
        
        // Create a new speaker object
        this.selectedSpeaker = {
            brand: brand,
            model: model,
            type: '',
            shape: '',
            price: '',
            amount: '',
            measurements: {},
            default_measurement: ''
        };
        this.isNewSpeaker = true;
        
        // Clear any existing selection
        document.querySelectorAll('.speaker-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Enable continue button
        const continueBtn = document.getElementById('continue-step-1');
        if (continueBtn) {
            continueBtn.disabled = false;
        }
        
        this.showNotification(`Created new speaker: ${brand} ${model}`, 'success');
    }
    
    populateMetadataForm() {
        if (!this.selectedSpeaker) return;
        
        // Update the current speaker info
        const speakerInfo = document.getElementById('current-speaker-info');
        if (speakerInfo) {
            speakerInfo.textContent = `Editing: ${this.selectedSpeaker.brand} ${this.selectedSpeaker.model}`;
        }
        
        // Populate form fields
        const form = document.getElementById('metadata-form');
        if (!form) return;
        
        form.querySelector('[name="brand"]').value = this.selectedSpeaker.brand || '';
        form.querySelector('[name="model"]').value = this.selectedSpeaker.model || '';
        form.querySelector('[name="type"]').value = this.selectedSpeaker.type || '';
        form.querySelector('[name="shape"]').value = this.selectedSpeaker.shape || '';
        const priceField = form.querySelector('[name="price"]');
        if (priceField) priceField.value = this.selectedSpeaker.price || '';
        const amountField = form.querySelector('[name="amount"]');
        if (amountField) amountField.value = this.selectedSpeaker.amount || '';
        
        // Populate measurements and set up tabs
        this.renderMeasurements();
        
        // Handle speaker type-specific field enabling/disabling
        this.handleSpeakerTypeChange();
    }

    setFieldValue(fieldId, value) {
        const field = document.getElementById(fieldId);
        if (field && value !== undefined && value !== null) {
            field.value = value;
        }
    }

    setCheckboxValue(fieldId, value) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.checked = Boolean(value);
        }
    }
    
    setupMeasurementTabListeners() {
        const tabsContainer = document.querySelector('#measurement-tabs .tabs ul');
        if (tabsContainer) {
            tabsContainer.addEventListener('click', (e) => {
                const tabLink = e.target.closest('a');
                if (tabLink) {
                    const tab = tabLink.closest('li');
                    const measurementName = tab.dataset.measurement;
                    if (measurementName) {
                        this.switchToMeasurementTab(measurementName);
                    }
                }
            });
        }
    }
    
    handleSpeakerTypeChange() {
        const speakerTypeSelect = document.querySelector('[name="type"]');
        if (!speakerTypeSelect) return;
        
        const speakerType = speakerTypeSelect.value;
        const isActive = speakerType === 'active';
        
        // Find sensitivity and impedance fields in both measurement and specifications sections
        const sensitivityFields = [
            document.getElementById('sensitivity'),
            document.getElementById('specifications_sensitivity')
        ];
        
        const impedanceFields = [
            document.getElementById('specifications_impedance')
        ];
        
        // Disable/enable sensitivity fields
        sensitivityFields.forEach(field => {
            if (field) {
                field.disabled = isActive;
                if (isActive) {
                    field.classList.add('is-disabled');
                    field.style.backgroundColor = '#f5f5f5';
                    field.style.color = '#999';
                    field.value = ''; // Clear value when disabled
                } else {
                    field.classList.remove('is-disabled');
                    field.style.backgroundColor = '';
                    field.style.color = '';
                }
            }
        });
        
        // Disable/enable impedance fields
        impedanceFields.forEach(field => {
            if (field) {
                field.disabled = isActive;
                if (isActive) {
                    field.classList.add('is-disabled');
                    field.style.backgroundColor = '#f5f5f5';
                    field.style.color = '#999';
                    field.value = ''; // Clear value when disabled
                } else {
                    field.classList.remove('is-disabled');
                    field.style.backgroundColor = '';
                    field.style.color = '';
                }
            }
        });
        
        // Update field labels to indicate why they're disabled
        const sensitivityLabels = document.querySelectorAll('label[for="sensitivity"], label[for="specifications_sensitivity"]');
        const impedanceLabels = document.querySelectorAll('label[for="specifications_impedance"]');
        
        sensitivityLabels.forEach(label => {
            if (label) {
                const originalText = label.textContent.replace(' (N/A for active speakers)', '');
                if (isActive) {
                    label.textContent = originalText + ' (N/A for active speakers)';
                    label.style.color = '#999';
                } else {
                    label.textContent = originalText;
                    label.style.color = '';
                }
            }
        });
        
        impedanceLabels.forEach(label => {
            if (label) {
                const originalText = label.textContent.replace(' (N/A for active speakers)', '');
                if (isActive) {
                    label.textContent = originalText + ' (N/A for active speakers)';
                    label.style.color = '#999';
                } else {
                    label.textContent = originalText;
                    label.style.color = '';
                }
            }
        });
    }
    
    addMeasurementTab(measurementName) {
        const tabsContainer = document.querySelector('#measurement-tabs .tabs ul');
        if (!tabsContainer) return;
        
        // Create new tab
        const newTab = document.createElement('li');
        newTab.dataset.measurement = measurementName;
        newTab.innerHTML = `
            <a>
                <span>${measurementName}</span>
                <button class="delete is-small ml-2" onclick="event.stopPropagation(); window.metadataManager.removeMeasurementTab('${measurementName}')"></button>
            </a>
        `;
        
        tabsContainer.appendChild(newTab);
        
        // Create corresponding form
        this.createMeasurementForm(measurementName);
    }
    
    createMeasurementForm(measurementName) {
        const container = document.getElementById('measurement-form-container');
        if (!container) return;
        
        // Check if form already exists for this measurement
        const existingForm = container.querySelector(`.measurement-form[data-measurement="${measurementName}"]`);
        if (existingForm) {
            return existingForm; // Form already exists, don't create a duplicate
        }
        
        // Clone the default measurement form
        const defaultForm = container.querySelector('.measurement-form[data-measurement="default"]');
        if (!defaultForm) return;
        
        const newForm = defaultForm.cloneNode(true);
        newForm.dataset.measurement = measurementName;
        newForm.classList.remove('is-active');
        
        // Update form field IDs to be unique and preserve their name attributes
        const fields = newForm.querySelectorAll('[id]');
        fields.forEach(field => {
            // Create unique ID by appending measurement name
            const baseId = field.id.replace(/-default$/, '');
            field.id = `${baseId}-${measurementName}`;
            
            // Clear any values from the template
            if (field.tagName === 'INPUT' || field.tagName === 'TEXTAREA' || field.tagName === 'SELECT') {
                if (field.type === 'checkbox' || field.type === 'radio') {
                    field.checked = false;
                } else {
                    field.value = '';
                }
            }
        });
        
        container.appendChild(newForm);
        return newForm;
    }
    
    switchToMeasurementTab(measurementName) {
        // Deactivate all tabs and forms
        const tabs = document.querySelectorAll('.measurement-tab');
        tabs.forEach(tab => tab.classList.remove('is-active'));
        
        const forms = document.querySelectorAll('.measurement-form');
        forms.forEach(form => form.classList.add('is-hidden'));
        
        // Activate the selected tab and form
        const selectedTab = document.querySelector(`.measurement-tab[data-measurement="${measurementName}"]`);
        if (selectedTab) {
            selectedTab.classList.add('is-active');
        }
        
        const selectedForm = document.getElementById(`measurement-form-${measurementName}`);
        if (selectedForm) {
            selectedForm.classList.remove('is-hidden');
            // Track the current active measurement
            this.currentMeasurement = measurementName;
            console.log(`Switched to measurement: ${measurementName}`);
        }
    }
    
    removeMeasurementTab(measurementName) {
        if (measurementName === 'default') return; // Can't remove default
        
        // Remove tab
        const tab = document.querySelector(`#measurement-tabs .tabs li[data-measurement="${measurementName}"]`);
        if (tab) tab.remove();
        
        // Remove form
        const form = document.querySelector(`.measurement-form[data-measurement="${measurementName}"]`);
        if (form) form.remove();
        
        // Remove from data
        if (this.selectedSpeaker.measurements) {
            delete this.selectedSpeaker.measurements[measurementName];
        }
        
        // Switch to default tab
        this.switchToMeasurementTab('default');
    }
    
    renderMeasurements() {
        const measurements = this.selectedSpeaker.measurements || {};
        const measurementNames = Object.keys(measurements);
        
        // Clear existing measurement tabs and forms
        document.getElementById('measurement-tabs').innerHTML = '';
        document.querySelectorAll('.measurement-form').forEach(form => {
            if (form.id !== 'measurement-form-template') {
                form.remove();
            }
        });
        
        // Create tabs for each measurement
        measurementNames.forEach((measurementName, index) => {
            // Create and add tab
            const tab = document.createElement('li');
            tab.classList.add('measurement-tab');
            tab.setAttribute('data-measurement', measurementName);
            if (index === 0) {
                tab.classList.add('is-active');
                // Set the initial current measurement
                this.currentMeasurement = measurementName;
            }
            
            const tabLink = document.createElement('a');
            tabLink.textContent = measurementName;
            tab.appendChild(tabLink);
            
            document.getElementById('measurement-tabs').appendChild(tab);
            
            // Create and populate form for this measurement
            this.createMeasurementForm(measurementName);
            
            // Set active state for the form
            const formContainer = document.getElementById('measurement-form-container');
            if (formContainer) {
                const form = formContainer.querySelector(`.measurement-form[data-measurement="${measurementName}"]`);
                if (form) {
                    form.classList.toggle('is-active', index === 0);
                }
            }
            
            // Populate the form with measurement data
            if (measurements[measurementName]) {
                this.populateMeasurementForm(measurementName, measurements[measurementName]);
            }
        });
        
        // Set up tab listeners
        this.setupMeasurementTabListeners();
    }
    
    populateMeasurementForm(measurementName, measurementData) {
        // Populate basic measurement fields
        this.setFieldValue(`origin-${measurementName}`, measurementData.origin);
        this.setFieldValue(`format-${measurementName}`, measurementData.format);
        this.setFieldValue(`review-${measurementName}`, measurementData.review);
        this.setFieldValue(`review_published-${measurementName}`, measurementData.review_published);
        this.setFieldValue(`quality-${measurementName}`, measurementData.quality);
        this.setFieldValue(`notes-${measurementName}`, measurementData.notes);
        this.setFieldValue(`symmetry-${measurementName}`, measurementData.symmetry);
        this.setFieldValue(`sensitivity-${measurementName}`, measurementData.sensitivity);
        this.setFieldValue(`scaled_flatness-${measurementName}`, measurementData.scaled_flatness);
        
        // Populate data acquisition fields
        const dataAcq = measurementData.data_acquisition || {};
        this.setFieldValue(`data_acquisition_via-${measurementName}`, dataAcq.via);
        this.setFieldValue(`data_acquisition_distance-${measurementName}`, dataAcq.distance);
        this.setFieldValue(`data_acquisition_signal-${measurementName}`, dataAcq.signal);
        this.setCheckboxValue(`data_acquisition_air_absorbtion-${measurementName}`, dataAcq.air_absorbtion);
        this.setFieldValue(`data_acquisition_resolution-${measurementName}`, dataAcq.resolution);
        this.setFieldValue(`data_acquisition_notes-${measurementName}`, dataAcq.notes);
        this.setFieldValue(`data_acquisition_min_valid_freq-${measurementName}`, dataAcq.min_valid_freq);
        this.setFieldValue(`data_acquisition_max_valid_freq-${measurementName}`, dataAcq.max_valid_freq);
        
        // Populate parameters
        const params = measurementData.parameters || {};
        this.setFieldValue(`parameters_mean_min-${measurementName}`, params.mean_min);
        this.setFieldValue(`parameters_mean_max-${measurementName}`, params.mean_max);
        
        // Populate extras
        const extras = measurementData.extras || {};
        this.setCheckboxValue(`extras_is_equed-${measurementName}`, extras.is_equed);
        this.setFieldValue(`extras_score_penalty-${measurementName}`, extras.score_penalty);
        
        // Populate specifications
        const specs = measurementData.specifications || {};
        this.setFieldValue(`specifications_sensitivity-${measurementName}`, specs.sensitivity);
        this.setFieldValue(`specifications_impedance-${measurementName}`, specs.impedance);
        this.setFieldValue(`specifications_weight-${measurementName}`, specs.weight);
        
        // Populate dispersion
        const dispersion = specs.dispersion || {};
        this.setFieldValue(`specifications_dispersion_horizontal-${measurementName}`, dispersion.horizontal);
        this.setFieldValue(`specifications_dispersion_vertical-${measurementName}`, dispersion.vertical);
        
        // Populate size
        const size = specs.size || {};
        this.setFieldValue(`specifications_size_height-${measurementName}`, size.height);
        this.setFieldValue(`specifications_size_width-${measurementName}`, size.width);
        this.setFieldValue(`specifications_size_depth-${measurementName}`, size.depth);
        
        // Populate SPL
        const spl = specs.SPL || {};
        this.setFieldValue(`specifications_spl_peak-${measurementName}`, spl.peak);
        this.setFieldValue(`specifications_spl_continuous-${measurementName}`, spl.continuous);
        this.setFieldValue(`specifications_spl_max-${measurementName}`, spl.max);
        
        // Populate preference rating
        const prefRating = measurementData.pref_rating || {};
        this.setFieldValue(`pref_rating_aad_on_axis-${measurementName}`, prefRating.aad_on_axis);
        this.setFieldValue(`pref_rating_nbd_on_axis-${measurementName}`, prefRating.nbd_on_axis);
        this.setFieldValue(`pref_rating_nbd_listening_window-${measurementName}`, prefRating.nbd_listening_window);
        this.setFieldValue(`pref_rating_nbd_sound_power-${measurementName}`, prefRating.nbd_sound_power);
        this.setFieldValue(`pref_rating_nbd_pred_in_room-${measurementName}`, prefRating.nbd_pred_in_room);
        this.setFieldValue(`pref_rating_sm_pred_in_room-${measurementName}`, prefRating.sm_pred_in_room);
        this.setFieldValue(`pref_rating_sm_sound_power-${measurementName}`, prefRating.sm_sound_power);
        this.setFieldValue(`pref_rating_pref_score-${measurementName}`, prefRating.pref_score);
        this.setFieldValue(`pref_rating_pref_score_wsub-${measurementName}`, prefRating.pref_score_wsub);
        this.setFieldValue(`pref_rating_lfx_hz-${measurementName}`, prefRating.lfx_hz);
        this.setFieldValue(`pref_rating_lfq-${measurementName}`, prefRating.lfq);
    }
    
    clearMeasurementForm() {
        // Clear all measurement form fields
        const formFields = [
            'origin', 'format', 'review', 'review_published', 'quality', 'notes', 
            'symmetry', 'sensitivity', 'scaled_flatness',
            'data_acquisition_via', 'data_acquisition_distance', 'data_acquisition_signal',
            'data_acquisition_resolution', 'data_acquisition_notes', 
            'data_acquisition_min_valid_freq', 'data_acquisition_max_valid_freq',
            'parameters_mean_min', 'parameters_mean_max',
            'extras_score_penalty',
            'specifications_sensitivity', 'specifications_impedance', 'specifications_weight',
            'specifications_dispersion_horizontal', 'specifications_dispersion_vertical',
            'specifications_size_height', 'specifications_size_width', 'specifications_size_depth',
            'specifications_spl_peak', 'specifications_spl_continuous', 'specifications_spl_max',
            'pref_rating_aad_on_axis', 'pref_rating_nbd_on_axis', 'pref_rating_nbd_listening_window',
            'pref_rating_nbd_sound_power', 'pref_rating_nbd_pred_in_room', 'pref_rating_sm_pred_in_room',
            'pref_rating_sm_sound_power', 'pref_rating_pref_score', 'pref_rating_pref_score_wsub',
            'pref_rating_lfx_hz', 'pref_rating_lfq'
        ];
        
        formFields.forEach(fieldId => {
            this.setFieldValue(fieldId, '');
        });
        
        // Clear checkboxes
        this.setCheckboxValue('data_acquisition_air_absorbtion', false);
        this.setCheckboxValue('extras_is_equed', false);
    }
    
    addMeasurement() {
        this.measurementCounter++;
        const name = `measurement-${this.measurementCounter}`;
        
        if (!this.selectedSpeaker.measurements) {
            this.selectedSpeaker.measurements = {};
        }
        
        this.selectedSpeaker.measurements[name] = {
            origin: '',
            format: 'klippel',
            quality: 'medium'
        };
        
        this.addMeasurementTab(name);
        this.switchToMeasurementTab(name);
    }
    
    removeMeasurement(name) {
        if (this.selectedSpeaker.measurements) {
            delete this.selectedSpeaker.measurements[name];
            this.renderMeasurements();
        }
    }
    
    saveMetadataForm() {
        const form = document.getElementById('metadata-form');
        if (!form) return;
        
        // Update speaker data from form
        this.selectedSpeaker.brand = form.querySelector('[name="brand"]').value;
        this.selectedSpeaker.model = form.querySelector('[name="model"]').value;
        this.selectedSpeaker.type = form.querySelector('[name="type"]').value;
        this.selectedSpeaker.shape = form.querySelector('[name="shape"]').value;
        const priceField2 = form.querySelector('[name="price"]');
        this.selectedSpeaker.price = priceField2 ? priceField2.value : '';
        const amountField2 = form.querySelector('[name="amount"]');
        this.selectedSpeaker.amount = amountField2 ? amountField2.value : '';
        
        // Save the current measurement data from the active form
        if (this.currentMeasurement) {
            // Initialize measurements object if needed
            if (!this.selectedSpeaker.measurements) {
                this.selectedSpeaker.measurements = {};
            }
            
            // Get data for the current measurement
            const measurementData = this.collectMeasurementData(this.currentMeasurement);
            
            // Save this measurement data
            this.selectedSpeaker.measurements[this.currentMeasurement] = measurementData;
            
            // Set default measurement if not set
            if (!this.selectedSpeaker.default_measurement && Object.keys(this.selectedSpeaker.measurements).length > 0) {
                this.selectedSpeaker.default_measurement = this.currentMeasurement;
            }
        }

        console.log('Saved speaker data:', this.selectedSpeaker);
    }
    
    collectMeasurementData(measurementName) {
        // Collect comprehensive measurement data for the specified measurement
        const measurementData = {
            // Required fields
            origin: (document.getElementById(`origin-${measurementName}`) && document.getElementById(`origin-${measurementName}`).value) || '',
            format: (document.getElementById(`format-${measurementName}`) && document.getElementById(`format-${measurementName}`).value) || 'klippel',
        };

        // Add optional fields if they have values
        const optionalFields = {
            review: document.getElementById(`review-${measurementName}`) && document.getElementById(`review-${measurementName}`).value,
            review_published: document.getElementById(`review_published-${measurementName}`) && document.getElementById(`review_published-${measurementName}`).value,
            quality: document.getElementById(`quality-${measurementName}`) && document.getElementById(`quality-${measurementName}`).value,
            notes: document.getElementById(`notes-${measurementName}`) && document.getElementById(`notes-${measurementName}`).value,
            symmetry: document.getElementById(`symmetry-${measurementName}`) && document.getElementById(`symmetry-${measurementName}`).value,
            sensitivity: this.parseNumber(document.getElementById(`sensitivity-${measurementName}`) && document.getElementById(`sensitivity-${measurementName}`).value),
            scaled_flatness: this.parseNumber(document.getElementById(`scaled_flatness-${measurementName}`) && document.getElementById(`scaled_flatness-${measurementName}`).value)
        }
        };

        // Add non-empty optional fields
        var optionalKeys = Object.keys(optionalFields);
        for (var i = 0; i < optionalKeys.length; i++) {
            var key = optionalKeys[i];
            if (optionalFields[key] !== undefined && optionalFields[key] !== '') {
                measurementData[key] = optionalFields[key];
            }
        }

        // Data acquisition
        const dataAcquisition = {
            via: document.getElementById(`data_acquisition_via-${measurementName}`) && document.getElementById(`data_acquisition_via-${measurementName}`).value,
            distance: this.parseNumber(document.getElementById(`data_acquisition_distance-${measurementName}`) && document.getElementById(`data_acquisition_distance-${measurementName}`).value),
            signal: document.getElementById(`data_acquisition_signal-${measurementName}`) && document.getElementById(`data_acquisition_signal-${measurementName}`).value,
            air_absorbtion: document.getElementById(`data_acquisition_air_absorbtion-${measurementName}`) && document.getElementById(`data_acquisition_air_absorbtion-${measurementName}`).checked,
            resolution: this.parseNumber(document.getElementById(`data_acquisition_resolution-${measurementName}`) && document.getElementById(`data_acquisition_resolution-${measurementName}`).value),
            notes: document.getElementById(`data_acquisition_notes-${measurementName}`) && document.getElementById(`data_acquisition_notes-${measurementName}`).value,
            min_valid_freq: this.parseNumber(document.getElementById(`data_acquisition_min_valid_freq-${measurementName}`) && document.getElementById(`data_acquisition_min_valid_freq-${measurementName}`).value),
            max_valid_freq: this.parseNumber(document.getElementById(`data_acquisition_max_valid_freq-${measurementName}`) && document.getElementById(`data_acquisition_max_valid_freq-${measurementName}`).value)
        };

        // Only add data_acquisition if it has meaningful data
        var cleanedDataAcquisition = {};
        var dataAcqKeys = Object.keys(dataAcquisition);
        for (var j = 0; j < dataAcqKeys.length; j++) {
            var key = dataAcqKeys[j];
            if (dataAcquisition[key] !== undefined && dataAcquisition[key] !== '' && dataAcquisition[key] !== false) {
                cleanedDataAcquisition[key] = dataAcquisition[key];
            }
        }
        if (Object.keys(cleanedDataAcquisition).length > 0) {
            measurementData.data_acquisition = cleanedDataAcquisition;
        }

        // Parameters
        const parameters = {
            mean_min: this.parseNumber(document.getElementById(`parameters_mean_min-${measurementName}`) && document.getElementById(`parameters_mean_min-${measurementName}`).value, true),
            mean_max: this.parseNumber(document.getElementById(`parameters_mean_max-${measurementName}`) && document.getElementById(`parameters_mean_max-${measurementName}`).value, true)
        };
        var cleanedParameters = {};
        var paramKeys = Object.keys(parameters);
        for (var k = 0; k < paramKeys.length; k++) {
            var key = paramKeys[k];
            if (parameters[key] !== undefined) {
                cleanedParameters[key] = parameters[key];
            }
        };
        if (Object.keys(cleanedParameters).length > 0) {
            measurementData.parameters = cleanedParameters;
        }

        // Extras
        var extras = {
            is_equed: document.getElementById(`extras_is_equed-${measurementName}`) && document.getElementById(`extras_is_equed-${measurementName}`).checked,
            score_penalty: this.parseNumber(document.getElementById(`extras_score_penalty-${measurementName}`) && document.getElementById(`extras_score_penalty-${measurementName}`).value)
        };
        var cleanedExtras = {};
        var extrasKeys = Object.keys(extras);
        for (var l = 0; l < extrasKeys.length; l++) {
            var key = extrasKeys[l];
            if (extras[key] !== undefined && extras[key] !== false && extras[key] !== '') {
                cleanedExtras[key] = extras[key];
            }
        };
        if (Object.keys(cleanedExtras).length > 0) {
            measurementData.extras = cleanedExtras;
        }

        // Specifications
        const specifications = {
            sensitivity: this.parseNumber(document.getElementById(`specifications_sensitivity-${measurementName}`) && document.getElementById(`specifications_sensitivity-${measurementName}`).value),
            impedance: this.parseNumber(document.getElementById(`specifications_impedance-${measurementName}`) && document.getElementById(`specifications_impedance-${measurementName}`).value),
            weight: this.parseNumber(document.getElementById(`specifications_weight-${measurementName}`) && document.getElementById(`specifications_weight-${measurementName}`).value)
        };

        // Dispersion
        var dispersion = {
            horizontal: this.parseNumber(document.getElementById(`specifications_dispersion_horizontal-${measurementName}`) && document.getElementById(`specifications_dispersion_horizontal-${measurementName}`).value),
            vertical: this.parseNumber(document.getElementById(`specifications_dispersion_vertical-${measurementName}`) && document.getElementById(`specifications_dispersion_vertical-${measurementName}`).value)
        };
        var cleanedDispersion = {};
        var dispersionKeys = Object.keys(dispersion);
        for (var m = 0; m < dispersionKeys.length; m++) {
            var key = dispersionKeys[m];
            if (dispersion[key] !== undefined && dispersion[key] !== '') {
                cleanedDispersion[key] = dispersion[key];
            }
        };
        if (Object.keys(cleanedDispersion).length > 0) {
            specifications.dispersion = cleanedDispersion;
        }

        // Size
        var size = {
            height: this.parseNumber(document.getElementById(`specifications_size_height-${measurementName}`) && document.getElementById(`specifications_size_height-${measurementName}`).value),
            width: this.parseNumber(document.getElementById(`specifications_size_width-${measurementName}`) && document.getElementById(`specifications_size_width-${measurementName}`).value),
            depth: this.parseNumber(document.getElementById(`specifications_size_depth-${measurementName}`) && document.getElementById(`specifications_size_depth-${measurementName}`).value)
        };
        var cleanedSize = {};
        var sizeKeys = Object.keys(size);
        for (var n = 0; n < sizeKeys.length; n++) {
            var key = sizeKeys[n];
            if (size[key] !== undefined && size[key] !== '') {
                cleanedSize[key] = size[key];
            }
        };
        if (Object.keys(cleanedSize).length > 0) {
            specifications.size = cleanedSize;
        }

        // SPL
        var spl = {
            peak: this.parseNumber(document.getElementById(`specifications_spl_peak-${measurementName}`) && document.getElementById(`specifications_spl_peak-${measurementName}`).value),
            continuous: this.parseNumber(document.getElementById(`specifications_spl_continuous-${measurementName}`) && document.getElementById(`specifications_spl_continuous-${measurementName}`).value),
            max: this.parseNumber(document.getElementById(`specifications_spl_max-${measurementName}`) && document.getElementById(`specifications_spl_max-${measurementName}`).value)
        };
        var cleanedSPL = {};
        var splKeys = Object.keys(spl);
        for (var p = 0; p < splKeys.length; p++) {
            var key = splKeys[p];
            if (spl[key] !== undefined && spl[key] !== '') {
                cleanedSPL[key] = spl[key];
            }
        };
        if (Object.keys(cleanedSPL).length > 0) {
            specifications.SPL = cleanedSPL;
        }

        // Only add specifications if it has meaningful data
        var cleanedSpecifications = {};
        var specKeys = Object.keys(specifications);
        for (var r = 0; r < specKeys.length; r++) {
            var key = specKeys[r];
            if (specifications[key] !== undefined && specifications[key] !== '' && 
                (typeof specifications[key] !== 'object' || Object.keys(specifications[key]).length > 0)) {
                cleanedSpecifications[key] = specifications[key];
            }
        }
        if (Object.keys(cleanedSpecifications).length > 0) {
            measurementData.specifications = cleanedSpecifications;
        }

        // Preference Rating
        var ratings = {
            bass: this.parseNumber(document.getElementById(`preference_rating_bass-${measurementName}`) && document.getElementById(`preference_rating_bass-${measurementName}`).value),
            dynamics: this.parseNumber(document.getElementById(`preference_rating_dynamics-${measurementName}`) && document.getElementById(`preference_rating_dynamics-${measurementName}`).value),
            highs: this.parseNumber(document.getElementById(`preference_rating_highs-${measurementName}`) && document.getElementById(`preference_rating_highs-${measurementName}`).value),
            midrange: this.parseNumber(document.getElementById(`preference_rating_midrange-${measurementName}`) && document.getElementById(`preference_rating_midrange-${measurementName}`).value),
            neutrality: this.parseNumber(document.getElementById(`preference_rating_neutrality-${measurementName}`) && document.getElementById(`preference_rating_neutrality-${measurementName}`).value),
            preference_score: this.parseNumber(document.getElementById(`preference_rating_preference_score-${measurementName}`) && document.getElementById(`preference_rating_preference_score-${measurementName}`).value)
        }
        var cleanedRatings = {};
        var ratingsKeys = Object.keys(ratings);
        for (var q = 0; q < ratingsKeys.length; q++) {
            var key = ratingsKeys[q];
            if (ratings[key] !== undefined && ratings[key] !== '') {
                cleanedRatings[key] = ratings[key];
            }
        };
        if (Object.keys(cleanedRatings).length > 0) {
            measurementData.pref_rating = cleanedRatings;
        }
        
        return measurementData;
    }

    parseNumber(value, isInteger = false) {
        if (!value || value === '') return undefined;
        const num = isInteger ? parseInt(value) : parseFloat(value);
        return isNaN(num) ? undefined : num;
    }
    
    async generatePythonCode() {
        if (!this.selectedSpeaker) return;
        
        const codePreview = document.getElementById('python-code');
        const writeButton = document.getElementById('write-metadata-btn');
        const validationDiv = document.getElementById('validation-status');
        if (!codePreview) return;
        
        // Validate speaker data first
        const validation = this.validateSpeakerData();
        
        // Show validation results
        if (validationDiv) {
            if (validation.valid) {
                validationDiv.innerHTML = `
                    <div class="notification is-success">
                        <strong>✅ Validation Passed!</strong> All data is valid and ready to write.
                    </div>
                `;
            } else {
                const errorList = validation.errors.map(error => `<li>${error}</li>`).join('');
                validationDiv.innerHTML = `
                    <div class="notification is-warning">
                        <strong>⚠️ Validation Issues Found:</strong>
                        <ul style="margin-top: 10px;">${errorList}</ul>
                        <p style="margin-top: 10px;"><em>Please fix these issues before writing to file.</em></p>
                    </div>
                `;
            }
        }
        
        // Generate Python dictionary code for preview
        const speakerCode = this.formatSpeakerAsPython(this.selectedSpeaker);
        const speakerId = this.generateSpeakerId(this.selectedSpeaker.brand, this.selectedSpeaker.model);
        const firstLetter = this.selectedSpeaker.brand[0].toLowerCase();
        const metadataFile = `metadata_${firstLetter}.py`;
        
        codePreview.textContent = `# This will be written to ${metadataFile}\n\n"${speakerId}": ${speakerCode}`;
        
        // Set default commit message
        const commitMessage = document.getElementById('commit-message');
        if (commitMessage && !commitMessage.value.trim()) {
            const action = this.isNewSpeaker ? 'Add' : 'Update';
            commitMessage.value = `${action} speaker metadata for ${this.selectedSpeaker.brand} ${this.selectedSpeaker.model}`;
        }
        
        // Enable/disable the write button based on validation
        if (writeButton) {
            writeButton.disabled = !validation.valid;
            if (validation.valid) {
                writeButton.textContent = this.isNewSpeaker ? 'Write New Speaker to File' : 'Update Speaker in File';
                writeButton.classList.remove('is-danger');
                writeButton.classList.add('is-primary');
            } else {
                writeButton.textContent = 'Fix Validation Errors First';
                writeButton.classList.remove('is-primary');
                writeButton.classList.add('is-danger');
            }
        }
    }
    
    validateSpeakerData() {
        if (!this.selectedSpeaker) return { valid: false, errors: ['No speaker selected'] };
        
        const errors = [];
        const speaker = this.selectedSpeaker;
        const speakerId = this.generateSpeakerId(speaker.brand, speaker.model);
        
        // Basic speaker validation
        if (!speaker.brand || speaker.brand.trim() === '') {
            errors.push('Brand is required');
        } else if (speaker.brand.endsWith(' ')) {
            errors.push('Brand has suspicious trailing space');
        }
        
        if (!speaker.model || speaker.model.trim() === '') {
            errors.push('Model is required');
        } else if (speaker.model.startsWith(' ')) {
            errors.push('Model has suspicious leading space');
        }
        
        // Check if speaker ID starts with brand
        if (speaker.brand && !speakerId.startsWith(speaker.brand)) {
            errors.push(`Speaker ID "${speakerId}" should start with brand "${speaker.brand}"`);
        }
        
        // Check if speaker ID ends with model
        if (speaker.model && !speakerId.endsWith(speaker.model)) {
            errors.push(`Speaker ID "${speakerId}" should end with model "${speaker.model}"`);
        }
        
        // Type validation
        const validTypes = ['active', 'passive'];
        if (!speaker.type || !validTypes.includes(speaker.type)) {
            errors.push(`Type must be one of: ${validTypes.join(', ')}`);
        }
        
        // Shape validation
        const validShapes = [
            'floorstanders', 'bookshelves', 'center', 'surround', 'omnidirectional',
            'columns', 'cbt', 'outdoor', 'panel', 'inwall', 'soundbar',
            'liveportable', 'toursound', 'cinema'
        ];
        if (!speaker.shape || !validShapes.includes(speaker.shape)) {
            errors.push(`Shape must be one of: ${validShapes.join(', ')}`);
        }
        
        // Amount validation
        const validAmounts = ['each', 'pair'];
        if (speaker.amount && !validAmounts.includes(speaker.amount)) {
            errors.push(`Amount must be one of: ${validAmounts.join(', ')}`);
        }
        
        // Measurements validation
        if (!speaker.measurements || Object.keys(speaker.measurements).length === 0) {
            errors.push('At least one measurement is required');
        } else {
            for (const [version, measurement] of Object.entries(speaker.measurements)) {
                const measurementErrors = this.validateMeasurement(speakerId, version, measurement);
                errors.push(...measurementErrors);
            }
        }
        
        // Default measurement validation
        if (speaker.default_measurement && speaker.measurements && 
            !speaker.measurements[speaker.default_measurement]) {
            errors.push(`Default measurement "${speaker.default_measurement}" not found in measurements`);
        }
        
        return { valid: errors.length === 0, errors };
    }
    
    validateMeasurement(speakerId, version, measurement) {
        const errors = [];
        
        // Required fields
        if (!measurement.origin || measurement.origin.trim() === '') {
            errors.push(`Measurement "${version}": Origin is required`);
        }
        
        if (!measurement.format || measurement.format.trim() === '') {
            errors.push(`Measurement "${version}": Format is required`);
        } else {
            const validFormats = ['klippel', 'princeton', 'webplotdigitizer', 'rew_text_dump', 'spl_hv_txt', 'gll_hv_txt'];
            if (!validFormats.includes(measurement.format)) {
                errors.push(`Measurement "${version}": Format must be one of: ${validFormats.join(', ')}`);
            }
        }
        
        // Quality validation
        if (measurement.quality) {
            const validQualities = ['unknown', 'low', 'medium', 'high'];
            if (!validQualities.includes(measurement.quality)) {
                errors.push(`Measurement "${version}": Quality must be one of: ${validQualities.join(', ')}`);
            }
        }
        
        // Symmetry validation
        if (measurement.symmetry) {
            const validSymmetries = ['coaxial', 'horizontal', 'vertical'];
            if (!validSymmetries.includes(measurement.symmetry)) {
                errors.push(`Measurement "${version}": Symmetry must be one of: ${validSymmetries.join(', ')}`);
            }
        }
        
        // Specifications validation
        if (measurement.specifications) {
            const specErrors = this.validateSpecifications(speakerId, version, measurement.specifications);
            errors.push(...specErrors);
        }
        
        // Review published date validation
        if (measurement.review_published) {
            if (measurement.review_published.length !== 8) {
                errors.push(`Measurement "${version}": Review published date should be 8 characters (YYYYMMDD)`);
            } else {
                try {
                    const year = parseInt(measurement.review_published.substring(0, 4));
                    const month = parseInt(measurement.review_published.substring(4, 6));
                    const day = parseInt(measurement.review_published.substring(6, 8));
                    const date = new Date(year, month - 1, day);
                    if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
                        errors.push(`Measurement "${version}": Review published date is not a valid date`);
                    }
                } catch (e) {
                    errors.push(`Measurement "${version}": Review published date is not a valid date`);
                }
            }
        }
        
        return errors;
    }
    
    validateSpecifications(speakerId, version, specs) {
        const errors = [];
        const validSpecKeys = ['dispersion', 'sensitivity', 'impedance', 'SPL', 'size', 'weight'];
        
        for (const [key, value] of Object.entries(specs)) {
            if (!validSpecKeys.includes(key)) {
                errors.push(`Measurement "${version}": Specification key "${key}" is not valid. Valid keys: ${validSpecKeys.join(', ')}`);
                continue;
            }
            
            switch (key) {
                case 'dispersion':
                    if (typeof value === 'object' && value !== null) {
                        for (const [direction, angle] of Object.entries(value)) {
                            if (!['horizontal', 'vertical'].includes(direction)) {
                                errors.push(`Measurement "${version}": Dispersion direction "${direction}" must be horizontal or vertical`);
                            }
                            const angleNum = parseFloat(angle);
                            if (isNaN(angleNum) || angleNum < 0 || angleNum > 180) {
                                errors.push(`Measurement "${version}": Dispersion angle "${angle}" must be between 0 and 180 degrees`);
                            }
                        }
                    }
                    break;
                    
                case 'sensitivity':
                    const sensitivity = parseFloat(value);
                    if (isNaN(sensitivity) || sensitivity < 20 || sensitivity >= 150) {
                        errors.push(`Measurement "${version}": Sensitivity "${value}" must be between 20 and 150 dB`);
                    }
                    break;
                    
                case 'impedance':
                    const impedance = parseFloat(value);
                    if (isNaN(impedance) || impedance <= 0 || impedance >= 50) {
                        errors.push(`Measurement "${version}": Impedance "${value}" must be between 0 and 50 ohms`);
                    }
                    break;
                    
                case 'SPL':
                    if (typeof value === 'object' && value !== null) {
                        const validSPLKeys = ['max', 'continuous', 'peak', 'm_noise', 'b_noise', 'pink_noise'];
                        for (const [state, spl] of Object.entries(value)) {
                            if (!validSPLKeys.includes(state)) {
                                errors.push(`Measurement "${version}": SPL parameter "${state}" must be one of: ${validSPLKeys.join(', ')}`);
                            }
                            const splNum = parseFloat(spl);
                            if (isNaN(splNum) || splNum < 0 || splNum >= 160) {
                                errors.push(`Measurement "${version}": SPL "${spl}" must be between 0 and 160 dB`);
                            }
                        }
                    }
                    break;
                    
                case 'size':
                    if (typeof value === 'object' && value !== null) {
                        const validDims = ['height', 'width', 'depth'];
                        for (const [dim, measurement] of Object.entries(value)) {
                            if (!validDims.includes(dim)) {
                                errors.push(`Measurement "${version}": Size dimension "${dim}" must be one of: ${validDims.join(', ')}`);
                            }
                            const dimNum = parseFloat(measurement);
                            if (isNaN(dimNum) || dimNum < 0 || dimNum > 2500) {
                                errors.push(`Measurement "${version}": Size "${measurement}" must be between 0 and 2500 mm`);
                            }
                        }
                    }
                    break;
                    
                case 'weight':
                    const weight = parseFloat(value);
                    if (isNaN(weight) || weight < 0 || weight > 500) {
                        errors.push(`Measurement "${version}": Weight "${value}" must be between 0 and 500 kg`);
                    }
                    break;
            }
        }
        
        return errors;
    }

    async writeMetadataToFile() {
        if (!this.selectedSpeaker) return;
        
        const writeButton = document.getElementById('write-metadata-btn');
        const statusDiv = document.getElementById('write-status');
        
        // Validate speaker data first
        const validation = this.validateSpeakerData();
        if (!validation.valid) {
            if (statusDiv) {
                const errorList = validation.errors.map(error => `<li>${error}</li>`).join('');
                statusDiv.innerHTML = `
                    <div class="notification is-danger">
                        <strong>Validation Failed!</strong> Please fix the following errors:
                        <ul style="margin-top: 10px;">${errorList}</ul>
                    </div>
                `;
            }
            return;
        }
        
        try {
            // Show loading state
            if (writeButton) {
                writeButton.disabled = true;
                writeButton.textContent = 'Writing...';
            }
            
            if (statusDiv) {
                statusDiv.innerHTML = '<div class="notification is-info">Writing metadata to file...</div>';
            }
            
            // Call the backend API to write metadata
            const response = await fetch('/api/write-metadata', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    speaker: this.selectedSpeaker,
                    is_update: !this.isNewSpeaker
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="notification is-success">
                            <strong>Success!</strong> ${result.message}
                            <br><strong>File:</strong> ${result.file}
                            <br><strong>Speaker ID:</strong> ${result.speaker_id}
                        </div>
                    `;
                }
                
                if (writeButton) {
                    writeButton.textContent = 'Metadata Written Successfully!';
                    writeButton.classList.remove('is-primary');
                    writeButton.classList.add('is-success');
                }
                
                // Enable git commit button
                const commitButton = document.getElementById('commit-btn');
                if (commitButton) {
                    commitButton.disabled = false;
                }
                
            } else {
                throw new Error(result.error || 'Failed to write metadata');
            }
            
        } catch (error) {
            console.error('Error writing metadata:', error);
            
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="notification is-danger">
                        <strong>Error:</strong> ${error.message}
                    </div>
                `;
            }
            
            if (writeButton) {
                writeButton.disabled = false;
                writeButton.textContent = this.isNewSpeaker ? 'Write New Speaker to File' : 'Update Speaker in File';
            }
        }
    }
    
    formatSpeakerAsPython(speaker) {
        const indent = '    ';
        let code = '{\n';
        
        code += `${indent}"brand": "${speaker.brand}",\n`;
        code += `${indent}"model": "${speaker.model}",\n`;
        code += `${indent}"type": "${speaker.type}",\n`;
        code += `${indent}"shape": "${speaker.shape}",\n`;
        
        if (speaker.price) {
            code += `${indent}"price": "${speaker.price}",\n`;
        }
        
        if (speaker.amount) {
            code += `${indent}"amount": "${speaker.amount}",\n`;
        }
        
        if (speaker.default_measurement) {
            code += `${indent}"default_measurement": "${speaker.default_measurement}",\n`;
        }
        
        if (speaker.measurements && Object.keys(speaker.measurements).length > 0) {
            code += `${indent}"measurements": {\n`;
            Object.entries(speaker.measurements).forEach(([name, data]) => {
                code += `${indent}${indent}"${name}": {\n`;
                
                // Basic measurement fields
                if (data.origin) code += `${indent}${indent}${indent}"origin": "${data.origin}",\n`;
                if (data.format) code += `${indent}${indent}${indent}"format": "${data.format}",\n`;
                if (data.review) code += `${indent}${indent}${indent}"review": "${data.review}",\n`;
                if (data.review_published) code += `${indent}${indent}${indent}"review_published": "${data.review_published}",\n`;
                if (data.quality) code += `${indent}${indent}${indent}"quality": "${data.quality}",\n`;
                if (data.notes) code += `${indent}${indent}${indent}"notes": "${data.notes}",\n`;
                if (data.symmetry) code += `${indent}${indent}${indent}"symmetry": "${data.symmetry}",\n`;
                if (data.sensitivity !== undefined) code += `${indent}${indent}${indent}"sensitivity": ${data.sensitivity},\n`;
                if (data.scaled_flatness !== undefined) code += `${indent}${indent}${indent}"scaled_flatness": ${data.scaled_flatness},\n`;
                
                // Data acquisition
                if (data.data_acquisition && Object.keys(data.data_acquisition).length > 0) {
                    code += `${indent}${indent}${indent}"data_acquisition": {\n`;
                    const da = data.data_acquisition;
                    if (da.via) code += `${indent}${indent}${indent}${indent}"via": "${da.via}",\n`;
                    if (da.distance !== undefined) code += `${indent}${indent}${indent}${indent}"distance": ${da.distance},\n`;
                    if (da.signal) code += `${indent}${indent}${indent}${indent}"signal": "${da.signal}",\n`;
                    if (da.air_absorbtion !== undefined) code += `${indent}${indent}${indent}${indent}"air_absorbtion": ${da.air_absorbtion},\n`;
                    if (da.resolution !== undefined) code += `${indent}${indent}${indent}${indent}"resolution": ${da.resolution},\n`;
                    if (da.notes) code += `${indent}${indent}${indent}${indent}"notes": "${da.notes}",\n`;
                    if (da.min_valid_freq !== undefined) code += `${indent}${indent}${indent}${indent}"min_valid_freq": ${da.min_valid_freq},\n`;
                    if (da.max_valid_freq !== undefined) code += `${indent}${indent}${indent}${indent}"max_valid_freq": ${da.max_valid_freq},\n`;
                    code += `${indent}${indent}${indent}},\n`;
                }
                
                // Parameters
                if (data.parameters && Object.keys(data.parameters).length > 0) {
                    code += `${indent}${indent}${indent}"parameters": {\n`;
                    const params = data.parameters;
                    if (params.mean_min !== undefined) code += `${indent}${indent}${indent}${indent}"mean_min": ${params.mean_min},\n`;
                    if (params.mean_max !== undefined) code += `${indent}${indent}${indent}${indent}"mean_max": ${params.mean_max},\n`;
                    code += `${indent}${indent}${indent}},\n`;
                }
                
                // Extras
                if (data.extras && Object.keys(data.extras).length > 0) {
                    code += `${indent}${indent}${indent}"extras": {\n`;
                    const extras = data.extras;
                    if (extras.is_equed !== undefined) code += `${indent}${indent}${indent}${indent}"is_equed": ${extras.is_equed},\n`;
                    if (extras.score_penalty !== undefined) code += `${indent}${indent}${indent}${indent}"score_penalty": ${extras.score_penalty},\n`;
                    code += `${indent}${indent}${indent}},\n`;
                }
                
                // Specifications
                if (data.specifications && Object.keys(data.specifications).length > 0) {
                    code += `${indent}${indent}${indent}"specifications": {\n`;
                    const specs = data.specifications;
                    if (specs.sensitivity !== undefined) code += `${indent}${indent}${indent}${indent}"sensitivity": ${specs.sensitivity},\n`;
                    if (specs.impedance !== undefined) code += `${indent}${indent}${indent}${indent}"impedance": ${specs.impedance},\n`;
                    if (specs.weight !== undefined) code += `${indent}${indent}${indent}${indent}"weight": ${specs.weight},\n`;
                    
                    // Dispersion
                    if (specs.dispersion && Object.keys(specs.dispersion).length > 0) {
                        code += `${indent}${indent}${indent}${indent}"dispersion": {\n`;
                        if (specs.dispersion.horizontal !== undefined) code += `${indent}${indent}${indent}${indent}${indent}"horizontal": ${specs.dispersion.horizontal},\n`;
                        if (specs.dispersion.vertical !== undefined) code += `${indent}${indent}${indent}${indent}${indent}"vertical": ${specs.dispersion.vertical},\n`;
                        code += `${indent}${indent}${indent}${indent}},\n`;
                    }
                    
                    // Size
                    if (specs.size && Object.keys(specs.size).length > 0) {
                        code += `${indent}${indent}${indent}${indent}"size": {\n`;
                        if (specs.size.height !== undefined) code += `${indent}${indent}${indent}${indent}${indent}"height": ${specs.size.height},\n`;
                        if (specs.size.width !== undefined) code += `${indent}${indent}${indent}${indent}${indent}"width": ${specs.size.width},\n`;
                        if (specs.size.depth !== undefined) code += `${indent}${indent}${indent}${indent}${indent}"depth": ${specs.size.depth},\n`;
                        code += `${indent}${indent}${indent}${indent}},\n`;
                    }
                    
                    // SPL
                    if (specs.SPL && Object.keys(specs.SPL).length > 0) {
                        code += `${indent}${indent}${indent}${indent}"SPL": {\n`;
                        if (specs.SPL.peak !== undefined) code += `${indent}${indent}${indent}${indent}${indent}"peak": ${specs.SPL.peak},\n`;
                        if (specs.SPL.continuous !== undefined) code += `${indent}${indent}${indent}${indent}${indent}"continuous": ${specs.SPL.continuous},\n`;
                        if (specs.SPL.max !== undefined) code += `${indent}${indent}${indent}${indent}${indent}"max": ${specs.SPL.max},\n`;
                        code += `${indent}${indent}${indent}${indent}},\n`;
                    }
                    
                    code += `${indent}${indent}${indent}},\n`;
                }
                
                // Preference Rating
                if (data.pref_rating && Object.keys(data.pref_rating).length > 0) {
                    code += `${indent}${indent}${indent}"pref_rating": {\n`;
                    const pref = data.pref_rating;
                    if (pref.aad_on_axis !== undefined) code += `${indent}${indent}${indent}${indent}"aad_on_axis": ${pref.aad_on_axis},\n`;
                    if (pref.nbd_on_axis !== undefined) code += `${indent}${indent}${indent}${indent}"nbd_on_axis": ${pref.nbd_on_axis},\n`;
                    if (pref.nbd_listening_window !== undefined) code += `${indent}${indent}${indent}${indent}"nbd_listening_window": ${pref.nbd_listening_window},\n`;
                    if (pref.nbd_sound_power !== undefined) code += `${indent}${indent}${indent}${indent}"nbd_sound_power": ${pref.nbd_sound_power},\n`;
                    if (pref.nbd_pred_in_room !== undefined) code += `${indent}${indent}${indent}${indent}"nbd_pred_in_room": ${pref.nbd_pred_in_room},\n`;
                    if (pref.sm_pred_in_room !== undefined) code += `${indent}${indent}${indent}${indent}"sm_pred_in_room": ${pref.sm_pred_in_room},\n`;
                    if (pref.sm_sound_power !== undefined) code += `${indent}${indent}${indent}${indent}"sm_sound_power": ${pref.sm_sound_power},\n`;
                    if (pref.pref_score !== undefined) code += `${indent}${indent}${indent}${indent}"pref_score": ${pref.pref_score},\n`;
                    if (pref.pref_score_wsub !== undefined) code += `${indent}${indent}${indent}${indent}"pref_score_wsub": ${pref.pref_score_wsub},\n`;
                    if (pref.lfx_hz !== undefined) code += `${indent}${indent}${indent}${indent}"lfx_hz": ${pref.lfx_hz},\n`;
                    if (pref.lfq !== undefined) code += `${indent}${indent}${indent}${indent}"lfq": ${pref.lfq},\n`;
                    code += `${indent}${indent}${indent}},\n`;
                }
                
                code += `${indent}${indent}},\n`;
            });
            code += `${indent}},\n`;
        }
        
        code += '}';
        return code;
    }
    
    generateSpeakerId(brand, model) {
        return `${brand} ${model}`.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    }
    
    async createGitCommit() {
        const commitMessage = document.getElementById('commit-message').value.trim();
        if (!commitMessage) {
            this.showNotification('Please enter a commit message', 'error');
            return;
        }
        
        const commitBtn = document.getElementById('create-commit-btn');
        const originalText = commitBtn.textContent;
        commitBtn.textContent = 'Creating commit...';
        commitBtn.disabled = true;
        
        try {
            // Prepare the export data
            const exportData = {
                changes: [['add', this.selectedSpeaker]],
                commitMessage: commitMessage
            };
            
            const response = await fetch('/api/export-metadata', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(exportData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Git commit created successfully!', 'success');
                
                // Show result
                const commitResult = document.getElementById('commit-result');
                if (commitResult) {
                    commitResult.innerHTML = `
                        <div class="notification is-success">
                            <h4 class="title is-5">Commit Created Successfully!</h4>
                            <p><strong>Branch:</strong> ${result.data.branch || 'N/A'}</p>
                            <p><strong>Commit:</strong> ${result.data.commit || 'N/A'}</p>
                            ${result.data.pr_url ? `<p><strong>Pull Request:</strong> <a href="${result.data.pr_url}" target="_blank">${result.data.pr_url}</a></p>` : ''}
                        </div>
                    `;
                    commitResult.style.display = 'block';
                }
            } else {
                throw new Error(result.message || 'Failed to create commit');
            }
        } catch (error) {
            console.error('Failed to create commit:', error);
            this.showNotification('Failed to create commit: ' + error.message, 'error');
        } finally {
            commitBtn.textContent = originalText;
            commitBtn.disabled = false;
        }
    }
    
    startOver() {
        this.selectedSpeaker = null;
        this.isNewSpeaker = false;
        this.measurementCounter = 0;
        
        // Clear form inputs
        document.getElementById('new-brand').value = '';
        document.getElementById('new-model').value = '';
        document.getElementById('speaker-search').value = '';
        document.getElementById('commit-message').value = '';
        
        // Clear selections
        document.querySelectorAll('.speaker-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Disable continue button
        const continueBtn = document.getElementById('continue-step-1');
        if (continueBtn) {
            continueBtn.disabled = true;
        }
        
        // Go back to step 1
        this.showStep(1);
        this.renderSpeakerList();
    }
    
    showNotification(message, type = 'info') {
        // Create a simple notification
        const notification = document.createElement('div');
        notification.className = `notification is-${type === 'error' ? 'danger' : type}`;
        notification.innerHTML = `
            <button class="delete"></button>
            ${message}
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Position it
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.maxWidth = '400px';
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
        
        // Add click to close
        const deleteBtn = notification.querySelector('.delete');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            });
        }
    }
}

// Initialize the metadata manager when the page loads
const manager = new SimpleMetadataManager();

export default SimpleMetadataManager;
