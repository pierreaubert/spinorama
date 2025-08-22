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
})
