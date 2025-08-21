# Speaker Metadata Manager

A web-based interface for managing speaker metadata in the Spinorama project. This tool allows you to add, edit, and remove speaker metadata with automatic validation and Git integration for creating pull requests.

## Features

- **Browse Speakers**: View and search through existing speaker metadata
- **Add New Speakers**: Create new speaker entries with comprehensive metadata
- **Edit Speakers**: Modify existing speaker information
- **Delete Speakers**: Remove speakers from the database
- **Validation**: Real-time validation of metadata according to Spinorama standards
- **Git Integration**: Automatic branch creation and commit generation for pull requests
- **Export Changes**: Generate Python code for metadata files

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-tests.txt
   pip install -r requirements-api.txt
   ```

2. **Start the Server**:
   ```bash
   python src/metadata/start.py 
   ```

3. **Open in Browser**:
   Navigate to `http://localhost:5000`

## File Structure

```
src/metadata/
├── metadata-manager.html          # Main HTML interface
├── metadata-manager.js            # Frontend JavaScript logic
├── metadata_api.py               # Backend API for metadata operations
├── metadata_server.py            # Flask server integration
├── start_metadata_manager.py     # Startup script
├── requirements.txt              # Python dependencies
└── METADATA_MANAGER_README.md    # This documentation
```

## Usage Guide

### Adding a New Speaker

1. Click the **"Add New Speaker"** tab
2. Fill in the required fields:
   - **Brand**: Manufacturer name (e.g., "KEF")
   - **Model**: Speaker model (e.g., "LS50 Meta")
   - **Type**: "passive" or "active"
   - **Shape**: Speaker form factor (bookshelves, floorstanders, etc.)
3. Add measurements using the **"Add Measurement"** button
4. Preview the JSON output in real-time
5. Click **"Add Speaker"** to save

### Editing Existing Speakers

1. Go to the **"Browse Speakers"** tab
2. Search for the speaker you want to edit
3. Click on the speaker in the list
4. Click **"Edit Speaker"** in the details panel
5. Make your changes in the **"Edit Speaker"** tab
6. Click **"Save Changes"**

### Exporting Changes

1. Navigate to the **"Export/Commit"** tab
2. Review your changes in the summary
3. Enter a descriptive commit message
4. Click **"Preview Files"** to see the generated Python code
5. Click **"Export Changes"** to create a Git branch and commit

## Metadata Structure

The metadata follows the TypedDict definitions in `datas/__init__.py`:

### Required Fields
- `brand`: Speaker manufacturer
- `model`: Speaker model name
- `type`: "passive" or "active"
- `shape`: Form factor (see valid shapes below)
- `default_measurement`: Name of the primary measurement
- `measurements`: Dictionary of measurement data

### Optional Fields
- `price`: Price in currency units
- `amount`: Pricing unit ("pair", "each", etc.)
- `skip`: Boolean to skip processing
- `default_eq`: Default EQ configuration
- `eqs`: Dictionary of EQ configurations
- `nearest`: List of similar speakers

### Valid Speaker Shapes
- `floorstanders`
- `bookshelves`
- `center`
- `surround`
- `omnidirectional`
- `columns`
- `cbt`
- `outdoor`
- `panel`
- `inwall`
- `soundbar`
- `liveportable`
- `toursound`
- `cinema`

### Measurement Formats
- `klippel`
- `webplotdigitizer`
- `spl_hv_txt`
- `gll_hv_txt`
- `princeton`
- `rew_text_dump`

### Quality Levels
- `low`
- `medium`
- `high`
- `unknown`

## API Endpoints

The backend provides RESTful API endpoints:

- `GET /api/speakers` - Get all speakers
- `GET /api/speakers/<id>` - Get specific speaker
- `POST /api/speakers` - Add new speaker
- `PUT /api/speakers/<id>` - Update speaker
- `DELETE /api/speakers/<id>` - Delete speaker
- `POST /api/export-metadata` - Export changes to Git
- `POST /api/validate-speaker` - Validate speaker data
- `GET /api/search-speakers` - Search speakers
- `GET /api/health` - Health check

## Git Integration

The system automatically:

1. Creates a new Git branch with timestamp
2. Updates the appropriate `metadata_*.py` files
3. Commits changes with your message
4. Provides the branch name for creating a pull request

### Branch Naming
Branches are named: `metadata-update-YYYYMMDD-HHMMSS`

### File Organization
Speakers are organized into files by the first letter of the brand name:
- `metadata_a.py` - Brands starting with 'A'
- `metadata_b.py` - Brands starting with 'B'
- etc.

## Validation Rules

The system enforces these validation rules:

1. **Required Fields**: Brand, model, type, shape must be provided
2. **Valid Enums**: Type, shape, format, and quality must match allowed values
3. **Measurements**: At least one measurement is required
4. **Measurement Data**: Each measurement needs origin and format
5. **Duplicates**: Prevents duplicate brand/model combinations

## Error Handling

- **Validation Errors**: Displayed in real-time with specific field feedback
- **API Errors**: Network and server errors are caught and displayed
- **Git Errors**: Branch creation and commit failures are reported
- **File Errors**: Issues with metadata file parsing are logged

## Development

### Adding New Features

1. **Frontend**: Modify `metadata-manager.js` for UI changes
2. **Backend**: Update `metadata_api.py` for new API functionality
3. **Server**: Extend `metadata_server.py` for new endpoints
4. **Validation**: Update validation rules in the API

### Testing

Test the system by:

1. Adding a test speaker with various field combinations
2. Editing existing speakers
3. Validating error handling with invalid data
4. Testing the export functionality
5. Verifying Git integration

### Debugging

- Check browser console for JavaScript errors
- Monitor Flask server output for API errors
- Verify Git status after export operations
- Validate generated Python syntax

## Troubleshooting

### Common Issues

1. **Dependencies Missing**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Git Errors**:
   - Ensure you're in a Git repository
   - Check Git configuration (user.name, user.email)
   - Verify write permissions

3. **Port Already in Use**:
   - Change port in `metadata_server.py`
   - Or stop other services using port 5000

4. **File Permissions**:
   - Ensure write access to `datas/` directory
   - Check Python execution permissions

### Getting Help

- Check the browser console for JavaScript errors
- Review Flask server logs for API issues
- Validate metadata structure against `datas/__init__.py`
- Test with minimal speaker data first

## Contributing

When contributing to this tool:

1. Follow the existing code style
2. Add validation for new fields
3. Update this documentation
4. Test thoroughly before submitting
5. Include example data for new features

## License

This tool is part of the Spinorama project and follows the same license terms.
