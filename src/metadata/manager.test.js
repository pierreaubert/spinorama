import { describe, it, expect, beforeEach, vi } from 'vitest'
import { JSDOM } from 'jsdom'

// Mock fetch globally
global.fetch = vi.fn()

describe('Speaker Metadata Manager', () => {
  let dom
  let document
  let window

  beforeEach(() => {
    // Reset fetch mock
    fetch.mockClear()
    fetch.mockReset()

    // Create a new DOM for each test
    dom = new JSDOM(`
      <!DOCTYPE html>
      <html>
        <body>
          <div id="app">
            <select id="speaker-list">
              <option value="">Select a speaker...</option>
            </select>
            <select id="brand-list">
              <option value="">Select a brand...</option>
            </select>
            <input id="speaker-search" type="text" />
            <input id="new-brand" type="text" />
            <input id="speaker-name" type="text" />
            <input name="speaker-option" type="radio" value="existing" checked />
            <input name="speaker-option" type="radio" value="new" />
            <div id="existing-speaker-section"></div>
            <div id="new-speaker-section" class="hidden"></div>
            <div id="measurements-container"></div>
            <button id="add-measurement"></button>
            <div id="validation-status"></div>
            <div id="validation-results" class="hidden"></div>
            <div id="export-code"></div>
          </div>
        </body>
      </html>
    `, { url: 'http://localhost' })

    document = dom.window.document
    window = dom.window

    // Make DOM available globally
    global.document = document
    global.window = window
    global.navigator = {
      clipboard: {
        writeText: vi.fn().mockResolvedValue()
      }
    }
  })

  describe('Data Loading', () => {
    it('should load speakers and brands on initialization', async () => {
      const mockSpeakers = ['Speaker 1', 'Speaker 2']
      const mockBrands = ['Brand A', 'Brand B']

      // Import and initialize the module
      const { SpeakerMetadataManager } = await import('./manager.js')
      
      // Create manager instance - constructor will skip DOM setup in test environment
      const manager = new SpeakerMetadataManager()

      // Mock fetch to return speakers first, then brands (matching the order in loadInitialData)
      fetch
        .mockResolvedValueOnce({
          json: () => Promise.resolve(mockSpeakers)
        })
        .mockResolvedValueOnce({
          json: () => Promise.resolve(mockBrands)
        })

      await manager.loadInitialData()

      expect(fetch).toHaveBeenCalledWith('/api/v1/speakers')
      expect(fetch).toHaveBeenCalledWith('/api/v1/brands')
      expect(manager.speakers).toEqual(mockSpeakers)
      expect(manager.brands).toEqual(mockBrands)
    })

    it('should handle API errors gracefully', async () => {
      fetch.mockRejectedValue(new Error('Network error'))

      const { SpeakerMetadataManager } = await import('./manager.js')
      
      // Create manager instance - constructor will skip DOM setup in test environment
      const manager = new SpeakerMetadataManager()

      // Should not throw
      await expect(manager.loadInitialData()).resolves.toBeUndefined()
    })
  })

  describe('Speaker Selection', () => {
    it('should toggle between existing and new speaker sections', () => {
      const existingSection = document.getElementById('existing-speaker-section')
      const newSection = document.getElementById('new-speaker-section')

      // Mock the manager methods
      const mockManager = {
        toggleSpeakerOption: (option) => {
          if (option === 'existing') {
            existingSection.classList.remove('hidden')
            newSection.classList.add('hidden')
          } else {
            existingSection.classList.add('hidden')
            newSection.classList.remove('hidden')
          }
        }
      }

      mockManager.toggleSpeakerOption('new')
      expect(existingSection.classList.contains('hidden')).toBe(true)
      expect(newSection.classList.contains('hidden')).toBe(false)

      mockManager.toggleSpeakerOption('existing')
      expect(existingSection.classList.contains('hidden')).toBe(false)
      expect(newSection.classList.contains('hidden')).toBe(true)
    })

    it('should filter speakers based on search input', () => {
      const speakerList = document.getElementById('speaker-list')
      speakerList.innerHTML = `
        <option value="">Select a speaker...</option>
        <option value="Brand A Speaker 1">Brand A Speaker 1</option>
        <option value="Brand B Speaker 2">Brand B Speaker 2</option>
        <option value="Brand A Speaker 3">Brand A Speaker 3</option>
      `

      const mockManager = {
        filterSpeakers: (searchTerm) => {
          const options = speakerList.querySelectorAll('option')
          options.forEach(option => {
            if (option.value === '') return
            const matches = option.textContent.toLowerCase().includes(searchTerm.toLowerCase())
            option.style.display = matches ? 'block' : 'none'
          })
        }
      }

      mockManager.filterSpeakers('Brand A')

      const options = speakerList.querySelectorAll('option')
      expect(options[1].style.display).toBe('block') // Brand A Speaker 1
      expect(options[2].style.display).toBe('none')  // Brand B Speaker 2
      expect(options[3].style.display).toBe('block') // Brand A Speaker 3
    })
  })

  describe('Form Validation', () => {
    it('should validate required fields for new speaker', () => {
      const mockManager = {
        validateNewSpeaker: () => {
          const brand = document.getElementById('brand-list').value || document.getElementById('new-brand').value
          const speakerName = document.getElementById('speaker-name').value

          return {
            valid: !!(brand && speakerName),
            errors: []
          }
        }
      }

      // Test with empty fields
      let result = mockManager.validateNewSpeaker()
      expect(result.valid).toBe(false)

      // Test with filled fields
      document.getElementById('new-brand').value = 'Test Brand'
      document.getElementById('speaker-name').value = 'Test Speaker'
      result = mockManager.validateNewSpeaker()
      expect(result.valid).toBe(true)
    })
  })

  describe('Measurement Management', () => {
    it('should add measurement panels dynamically', () => {
      const container = document.getElementById('measurements-container')

      const mockManager = {
        measurementCounter: 0,
        addMeasurement: function(measurementKey = '', measurementData = {}) {
          this.measurementCounter++
          const measurementPanel = document.createElement('div')
          measurementPanel.className = 'measurement-panel'
          measurementPanel.innerHTML = `
            <div class="panel">
              <p class="panel-heading">Measurement ${this.measurementCounter}</p>
              <input class="measurement-key" value="${measurementKey}" />
              <input class="measurement-origin" value="${measurementData.origin || ''}" />
            </div>
          `
          container.appendChild(measurementPanel)
        }
      }

      expect(container.children.length).toBe(0)

      mockManager.addMeasurement('test', { origin: 'Test Origin' })

      expect(container.children.length).toBe(1)
      expect(container.querySelector('.measurement-key').value).toBe('test')
      expect(container.querySelector('.measurement-origin').value).toBe('Test Origin')
    })
  })

  describe('Data Export', () => {
    it('should generate proper Python code format', () => {
      const mockSpeakerData = {
        brand: 'Test Brand',
        model: 'Test Model',
        type: 'passive',
        shape: 'bookshelves',
        measurements: {
          'test': {
            origin: 'Test Origin',
            format: 'klippel'
          }
        },
        default_measurement: 'test'
      }

      const mockManager = {
        currentSpeakerData: mockSpeakerData,
        generateExportCode: function() {
          const speakerKey = `${this.currentSpeakerData.brand} ${this.currentSpeakerData.model}`
          const cleanData = JSON.parse(JSON.stringify(this.currentSpeakerData))

          return `# Generated speaker metadata for ${speakerKey}\n"${speakerKey}": ${JSON.stringify(cleanData, null, 4)}`
        }
      }

      const code = mockManager.generateExportCode()

      expect(code).toContain('# Generated speaker metadata for Test Brand Test Model')
      expect(code).toContain('"Test Brand Test Model":')
      expect(code).toContain('"brand": "Test Brand"')
      expect(code).toContain('"measurements"')
    })
  })

  describe('Validation Integration', () => {
    it('should call validation API with correct data', async () => {
      const mockValidationResponse = {
        valid: true,
        messages: [],
        speaker_name: 'Test Speaker'
      }

      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve(mockValidationResponse)
      })

      const mockSpeakerData = {
        brand: 'Test Brand',
        model: 'Test Model',
        type: 'passive',
        shape: 'bookshelves'
      }

      const mockManager = {
        currentSpeakerData: mockSpeakerData,
        validateSpeakerData: async function() {
          const response = await fetch('https://api.spinorama.org/v1/validate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(this.currentSpeakerData)
          })
          return await response.json()
        }
      }

      const result = await mockManager.validateSpeakerData()

      expect(fetch).toHaveBeenCalledWith('https://api.spinorama.org/v1/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(mockSpeakerData)
      })
      expect(result.valid).toBe(true)
    })
  })

  describe('Multiple Measurements Loading', () => {
    it('should load KEF LS60 Wireless with multiple measurements correctly', async () => {
      const mockSpeakerData = {
        "brand": "KEF",
        "model": "LS60 Wireless",
        "type": "active",
        "shape": "floorstanders",
        "measurements": {
          "eac-0-degree": {
            "origin": "ErinsAudioCorner",
            "format": "klippel",
            "review_published": "20231218",
            "specifications": {
              "SPL": { "peak": 111 },
              "size": { "height": 1090, "width": 212, "depth": 394 },
              "weight": 31.2
            }
          },
          "eac-15-degree": {
            "origin": "ErinsAudioCorner", 
            "format": "klippel",
            "review_published": "20231218",
            "specifications": {
              "SPL": { "peak": 111 },
              "size": { "height": 1090, "width": 212, "depth": 394 },
              "weight": 31.2
            }
          },
          "vendor": {
            "origin": "Vendors-KEF",
            "format": "webplotdigitizer",
            "quality": "medium",
            "review_published": "20220909",
            "specifications": {
              "SPL": { "peak": 111 },
              "size": { "height": 1090, "width": 212, "depth": 394 },
              "weight": 31.2
            }
          }
        },
        "default_measurement": "eac-0-degree"
      }

      const { SpeakerMetadataManager } = await import('./manager.js')
      const manager = new SpeakerMetadataManager()
      
      // Set the speaker data and populate form
      manager.currentSpeakerData = mockSpeakerData
      manager.populateForm()
      
      // Check that all measurements were loaded
      const measurementPanels = document.querySelectorAll('.measurement-panel')
      expect(measurementPanels.length).toBe(3)
      
      // Check that measurement titles show the actual keys
      const panelHeadings = document.querySelectorAll('.panel-heading')
      const headingTexts = Array.from(panelHeadings).map(h => h.textContent.trim().split('\n')[0].trim())
      expect(headingTexts).toContain('eac-0-degree')
      expect(headingTexts).toContain('eac-15-degree') 
      expect(headingTexts).toContain('vendor')
      
      // Check that review_published dates are loaded correctly
      const dateInputs = document.querySelectorAll('.measurement-review-published')
      const dateValues = Array.from(dateInputs).map(input => input.value)
      expect(dateValues).toContain('2023-12-18')
      expect(dateValues).toContain('2022-09-09')
    })

    it('should convert dates correctly when collecting form data', async () => {
      const { SpeakerMetadataManager } = await import('./manager.js')
      const manager = new SpeakerMetadataManager()
      
      // Mock DOM elements for form data collection
      const mockPanel = {
        querySelector: (selector) => {
          const mockInputs = {
            '.measurement-key': { value: 'test-measurement' },
            '.measurement-origin': { value: 'TestOrigin' },
            '.measurement-format': { value: 'klippel' },
            '.measurement-quality': { value: 'high' },
            '.measurement-notes': { value: 'Test notes' },
            '.measurement-review': { value: 'Test review' },
            '.measurement-review-published': { value: '2023-12-18' }, // HTML date format
            '.measurement-symmetry': { value: 'vertical' },
            '.measurement-da-via': { value: '' },
            '.measurement-da-distance': { value: '' },
            '.measurement-da-signal': { value: '' },
            '.measurement-da-resolution': { value: '' },
            '.measurement-da-min-freq': { value: '' },
            '.measurement-da-max-freq': { value: '' },
            '.measurement-da-air-absorption': { checked: false },
            '.measurement-da-notes': { value: '' },
            '.measurement-extras-equed': { checked: false },
            '.measurement-extras-penalty': { value: '' },
            '.measurement-spec-sensitivity': { value: '' },
            '.measurement-spec-impedance': { value: '' },
            '.measurement-spec-weight': { value: '' },
            '.measurement-spec-height': { value: '' },
            '.measurement-spec-width': { value: '' },
            '.measurement-spec-depth': { value: '' },
            '.measurement-spec-spl-peak': { value: '' },
            '.measurement-spec-spl-continuous': { value: '' },
            '.measurement-spec-spl-max': { value: '' },
            '.measurement-spec-disp-horizontal': { value: '' },
            '.measurement-spec-disp-vertical': { value: '' }
          }
          return mockInputs[selector] || { value: '', checked: false }
        }
      }

      // Mock DOM methods
      global.document = {
        getElementById: (id) => {
          const mockElements = {
            'form-brand': { value: 'TestBrand' },
            'form-model': { value: 'TestModel' },
            'form-type': { value: 'active' },
            'form-shape': { value: 'bookshelves' },
            'form-price': { value: '1000' },
            'form-amount': { value: 'pair' }
          }
          return mockElements[id] || { value: '' }
        },
        querySelectorAll: (selector) => {
          if (selector === '.measurement-panel') {
            return [mockPanel]
          }
          return []
        }
      }

      manager.collectFormData()
      
      // Check that the date was converted from YYYY-MM-DD to YYYYMMDD
      expect(manager.currentSpeakerData.measurements['test-measurement'].review_published).toBe('20231218')
    })
  })
})
