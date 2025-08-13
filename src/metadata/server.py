#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI server for Speaker Metadata Management
Integrates with the existing Spinorama website
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from metadata.api import MetadataAPI


def format_speaker_as_python(speaker: Dict[str, Any], indent: str = "    ") -> str:
    """Format speaker data as Python dictionary code"""
    code = "{\n"

    # Basic speaker fields
    code += f'{indent}    "brand": "{speaker["brand"]}",\n'
    code += f'{indent}    "model": "{speaker["model"]}",\n'
    code += f'{indent}    "type": "{speaker["type"]}",\n'
    code += f'{indent}    "shape": "{speaker["shape"]}",\n'

    if speaker.get("price"):
        code += f'{indent}    "price": "{speaker["price"]}",\n'

    if speaker.get("amount"):
        code += f'{indent}    "amount": "{speaker["amount"]}",\n'

    if speaker.get("default_measurement"):
        code += f'{indent}    "default_measurement": "{speaker["default_measurement"]}",\n'

    if speaker.get("measurements") and isinstance(speaker["measurements"], dict):
        code += f'{indent}    "measurements": {{\n'
        for name, data in speaker["measurements"].items():
            code += f'{indent}        "{name}": {{\n'

            # Basic measurement fields
            if data.get("origin"):
                code += f'{indent}            "origin": "{data["origin"]}",\n'
            if data.get("format"):
                code += f'{indent}            "format": "{data["format"]}",\n'
            if data.get("review"):
                code += f'{indent}            "review": "{data["review"]}",\n'
            if data.get("review_published"):
                code += f'{indent}            "review_published": "{data["review_published"]}",\n'
            if data.get("quality"):
                code += f'{indent}            "quality": "{data["quality"]}",\n'
            if data.get("notes"):
                code += f'{indent}            "notes": "{data["notes"]}",\n'
            if data.get("symmetry"):
                code += f'{indent}            "symmetry": "{data["symmetry"]}",\n'
            if data.get("sensitivity") is not None:
                code += f'{indent}            "sensitivity": {data["sensitivity"]},\n'
            if data.get("scaled_flatness") is not None:
                code += f'{indent}            "scaled_flatness": {data["scaled_flatness"]},\n'

            # Data acquisition
            if data.get("data_acquisition") and isinstance(data["data_acquisition"], dict):
                da = data["data_acquisition"]
                code += f'{indent}            "data_acquisition": {{\n'
                if da.get("via"):
                    code += f'{indent}                "via": "{da["via"]}",\n'
                if da.get("distance") is not None:
                    code += f'{indent}                "distance": {da["distance"]},\n'
                if da.get("signal"):
                    code += f'{indent}                "signal": "{da["signal"]}",\n'
                if da.get("air_absorbtion") is not None:
                    code += f'{indent}                "air_absorbtion": {da["air_absorbtion"]},\n'
                if da.get("resolution") is not None:
                    code += f'{indent}                "resolution": {da["resolution"]},\n'
                if da.get("notes"):
                    code += f'{indent}                "notes": "{da["notes"]}",\n'
                if da.get("min_valid_freq") is not None:
                    code += f'{indent}                "min_valid_freq": {da["min_valid_freq"]},\n'
                if da.get("max_valid_freq") is not None:
                    code += f'{indent}                "max_valid_freq": {da["max_valid_freq"]},\n'
                code += f"{indent}            }},\n"

            # Parameters
            if data.get("parameters") and isinstance(data["parameters"], dict):
                params = data["parameters"]
                code += f'{indent}            "parameters": {{\n'
                if params.get("mean_min") is not None:
                    code += f'{indent}                "mean_min": {params["mean_min"]},\n'
                if params.get("mean_max") is not None:
                    code += f'{indent}                "mean_max": {params["mean_max"]},\n'
                code += f"{indent}            }},\n"

            # Extras
            if data.get("extras") and isinstance(data["extras"], dict):
                extras = data["extras"]
                code += f'{indent}            "extras": {{\n'
                if extras.get("is_equed") is not None:
                    code += (
                        f'{indent}                "is_equed": {str(extras["is_equed"]).lower()},\n'
                    )
                if extras.get("score_penalty") is not None:
                    code += f'{indent}                "score_penalty": {extras["score_penalty"]},\n'
                code += f"{indent}            }},\n"

            # Specifications
            if data.get("specifications") and isinstance(data["specifications"], dict):
                specs = data["specifications"]
                code += f'{indent}            "specifications": {{\n'
                if specs.get("sensitivity") is not None:
                    code += f'{indent}                "sensitivity": {specs["sensitivity"]},\n'
                if specs.get("impedance") is not None:
                    code += f'{indent}                "impedance": {specs["impedance"]},\n'
                if specs.get("weight") is not None:
                    code += f'{indent}                "weight": {specs["weight"]},\n'

                # Dispersion
                if specs.get("dispersion") and isinstance(specs["dispersion"], dict):
                    disp = specs["dispersion"]
                    code += f'{indent}                "dispersion": {{\n'
                    if disp.get("horizontal") is not None:
                        code += f'{indent}                    "horizontal": {disp["horizontal"]},\n'
                    if disp.get("vertical") is not None:
                        code += f'{indent}                    "vertical": {disp["vertical"]},\n'
                    code += f"{indent}                }},\n"

                # Size
                if specs.get("size") and isinstance(specs["size"], dict):
                    size = specs["size"]
                    code += f'{indent}                "size": {{\n'
                    if size.get("height") is not None:
                        code += f'{indent}                    "height": {size["height"]},\n'
                    if size.get("width") is not None:
                        code += f'{indent}                    "width": {size["width"]},\n'
                    if size.get("depth") is not None:
                        code += f'{indent}                    "depth": {size["depth"]},\n'
                    code += f"{indent}                }},\n"

                # SPL
                if specs.get("SPL") and isinstance(specs["SPL"], dict):
                    spl = specs["SPL"]
                    code += f'{indent}                "SPL": {{\n'
                    if spl.get("peak") is not None:
                        code += f'{indent}                    "peak": {spl["peak"]},\n'
                    if spl.get("continuous") is not None:
                        code += f'{indent}                    "continuous": {spl["continuous"]},\n'
                    if spl.get("max") is not None:
                        code += f'{indent}                    "max": {spl["max"]},\n'
                    code += f"{indent}                }},\n"

                code += f"{indent}            }},\n"

            # Preference Rating
            if data.get("pref_rating") and isinstance(data["pref_rating"], dict):
                pref = data["pref_rating"]
                code += f'{indent}            "pref_rating": {{\n'
                if pref.get("aad_on_axis") is not None:
                    code += f'{indent}                "aad_on_axis": {pref["aad_on_axis"]},\n'
                if pref.get("nbd_on_axis") is not None:
                    code += f'{indent}                "nbd_on_axis": {pref["nbd_on_axis"]},\n'
                if pref.get("nbd_listening_window") is not None:
                    code += f'{indent}                "nbd_listening_window": {pref["nbd_listening_window"]},\n'
                if pref.get("nbd_sound_power") is not None:
                    code += (
                        f'{indent}                "nbd_sound_power": {pref["nbd_sound_power"]},\n'
                    )
                if pref.get("nbd_pred_in_room") is not None:
                    code += (
                        f'{indent}                "nbd_pred_in_room": {pref["nbd_pred_in_room"]},\n'
                    )
                if pref.get("sm_pred_in_room") is not None:
                    code += (
                        f'{indent}                "sm_pred_in_room": {pref["sm_pred_in_room"]},\n'
                    )
                if pref.get("sm_sound_power") is not None:
                    code += f'{indent}                "sm_sound_power": {pref["sm_sound_power"]},\n'
                if pref.get("pref_score") is not None:
                    code += f'{indent}                "pref_score": {pref["pref_score"]},\n'
                if pref.get("pref_score_wsub") is not None:
                    code += (
                        f'{indent}                "pref_score_wsub": {pref["pref_score_wsub"]},\n'
                    )
                if pref.get("lfx_hz") is not None:
                    code += f'{indent}                "lfx_hz": {pref["lfx_hz"]},\n'
                if pref.get("lfq") is not None:
                    code += f'{indent}                "lfq": {pref["lfq"]},\n'
                code += f"{indent}            }},\n"

            code += f"{indent}        }},\n"
        code += f"{indent}    }},\n"

    code += f"{indent}}}"
    return code


# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


# Pydantic models for request/response validation
class SpeakerData(BaseModel):
    brand: str
    model: str
    type: str
    shape: str
    price: Optional[str] = None
    amount: Optional[str] = None
    default_measurement: str
    measurements: Dict[str, Dict[str, Any]]
    skip: Optional[bool] = None
    default_eq: Optional[str] = None
    eqs: Optional[Dict[str, Any]] = None
    nearest: Optional[List[tuple]] = None


class ExportRequest(BaseModel):
    changes: List[tuple]
    commitMessage: str


def create_app():
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="Spinorama Metadata Manager",
        description="API for managing speaker metadata",
        version="1.0.0",
    )

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize the metadata API
    metadata_api = MetadataAPI()

    # Serve static files
    website_dir = Path(__file__).parent

    @app.get("/")
    async def index():
        return HTMLResponse(content=open(website_dir / "manager.html").read())

    @app.get("/manager.js")
    async def serve_metadata_js():
        file_path = website_dir / "manager.js"
        if file_path.exists():
            with open(file_path, "r") as f:
                content = f.read()
            return Response(content=content, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="JavaScript file not found")

    @app.get("/js/{filename}")
    async def serve_js(filename: str):
        file_path = website_dir / filename
        if file_path.exists():
            return HTMLResponse(content=open(file_path).read())
        raise HTTPException(status_code=404, detail="File not found")

    @app.get("/css/{filename}")
    async def serve_css(filename: str):
        # Look for CSS files in the css directory
        css_dir = website_dir / "../../dist/css"
        file_path = css_dir / filename
        if file_path.exists() and file_path.suffix == ".css":
            with open(file_path, "r") as f:
                content = f.read()
            return Response(content=content, media_type="text/css")
        raise HTTPException(status_code=404, detail="CSS file not found")

    # API Routes
    @app.get("/api/speakers")
    async def get_speakers():
        """Get all speakers"""
        try:
            speakers = metadata_api.get_all_speakers()
            return {"success": True, "data": speakers}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/api/speakers/{speaker_id}")
    async def get_speaker(speaker_id: str):
        """Get a specific speaker by ID"""
        try:
            speaker = metadata_api.get_speaker(speaker_id)
            if speaker:
                return {"success": True, "data": speaker}
            else:
                raise HTTPException(status_code=404, detail="Speaker not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/speakers")
    async def add_speaker(speaker_data: SpeakerData):
        """Add a new speaker"""
        try:
            # Convert Pydantic model to dict
            speaker_dict = speaker_data.dict(exclude_unset=True)

            # Validate data
            errors = metadata_api.validate_speaker_data(speaker_dict)
            if errors:
                raise HTTPException(status_code=400, detail={"errors": errors})

            result = metadata_api.add_speaker(speaker_dict)
            return {"success": True, "data": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.put("/api/speakers/{speaker_id}")
    async def update_speaker(speaker_id: str, speaker_data: SpeakerData):
        """Update an existing speaker"""
        try:
            # Convert Pydantic model to dict
            speaker_dict = speaker_data.dict(exclude_unset=True)

            # Validate data
            errors = metadata_api.validate_speaker_data(speaker_dict)
            if errors:
                raise HTTPException(status_code=400, detail={"errors": errors})

            result = metadata_api.update_speaker(speaker_id, speaker_dict)
            return {"success": True, "data": result}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.delete("/api/speakers/{speaker_id}")
    async def delete_speaker(speaker_id: str):
        """Delete a speaker"""
        try:
            result = metadata_api.delete_speaker(speaker_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        else:
            return {"success": True, "data": result}

    @app.post("/api/export-metadata")
    async def export_metadata(export_data: ExportRequest):
        """Export metadata changes to Git"""
        try:
            if not export_data.changes:
                raise HTTPException(status_code=400, detail="No changes to export")

            if not export_data.commitMessage.strip():
                raise HTTPException(status_code=400, detail="Commit message is required")

            result = metadata_api.export_changes(export_data.changes, export_data.commitMessage)
            return {"success": True, "data": result}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/validate-speaker")
    async def validate_speaker(speaker_data: SpeakerData):
        """Validate speaker data without saving"""
        try:
            # Convert Pydantic model to dict
            speaker_dict = speaker_data.dict(exclude_unset=True)

            errors = metadata_api.validate_speaker_data(speaker_dict)

            if errors:
                return {"success": False, "errors": errors}
            else:
                return {"success": True, "message": "Speaker data is valid"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/api/search-speakers")
    async def search_speakers(q: str = "", type: str = "", shape: str = ""):
        """Search speakers by brand, model, or other criteria"""
        try:
            query = q.lower()
            speaker_type = type
            speaker_shape = shape

            all_speakers = metadata_api.get_all_speakers()
            filtered_speakers = []

            for speaker in all_speakers:
                # Text search
                if query:
                    search_text = f"{speaker.get('brand', '')} {speaker.get('model', '')}".lower()
                    if query not in search_text:
                        continue

                # Type filter
                if speaker_type and speaker.get("type") != speaker_type:
                    continue

                # Shape filter
                if speaker_shape and speaker.get("shape") != speaker_shape:
                    continue

                filtered_speakers.append(speaker)

            return {"success": True, "data": filtered_speakers}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/write-metadata")
    async def write_metadata(request: Request):
        """Write speaker metadata to the appropriate metadata file"""
        try:
            data = await request.json()
            speaker_data = data.get("speaker")
            is_update = data.get("is_update", False)

            if not speaker_data:
                raise HTTPException(status_code=400, detail="Speaker data is required")

            brand = speaker_data.get("brand", "").strip()
            model = speaker_data.get("model", "").strip()

            if not brand or not model:
                raise HTTPException(status_code=400, detail="Brand and model are required")

            # Determine the metadata file based on the first letter of the brand
            first_letter = brand[0].lower()
            if not first_letter.isalpha():
                first_letter = "z"  # Put non-alphabetic brands in metadata_z.py

            metadata_file = f"metadata_{first_letter}.py"
            metadata_path = os.path.join(os.path.dirname(__file__), metadata_file)

            # Generate speaker ID
            speaker_id = f"{brand} {model}"

            # Read existing metadata file
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                # Create new metadata file if it doesn't exist
                content = f"""# -*- coding: utf-8 -*-
from . import SpeakerDatabase, gll_data_acquisition_std

speakers_info_{first_letter}: SpeakerDatabase = {{
}}
"""

            # Generate Python code for the speaker
            speaker_code = format_speaker_as_python(speaker_data, indent="    ")

            # Check if speaker already exists
            speaker_exists = f'"{speaker_id}":' in content

            if speaker_exists and is_update:
                # Replace existing speaker entry
                import re

                # Find the speaker entry and replace it
                pattern = rf'"{re.escape(speaker_id)}":\s*\{{[^}}]*(?:\{{[^}}]*\}}[^}}]*)*\}},'
                replacement = f'"{speaker_id}": {speaker_code},'
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            elif not speaker_exists:
                # Add new speaker entry
                # Find the closing brace of the dictionary
                dict_end = content.rfind("}")
                if dict_end != -1:
                    # Insert before the closing brace
                    new_entry = f'    "{speaker_id}": {speaker_code},\n'
                    content = content[:dict_end] + new_entry + content[dict_end:]
            else:
                return {
                    "success": False,
                    "error": f"Speaker '{speaker_id}' already exists. Use update mode to modify existing speakers.",
                }

            # Write the updated content back to the file
            with open(metadata_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "message": f"Speaker metadata {'updated' if is_update else 'added'} in {metadata_file}",
                "file": metadata_file,
                "speaker_id": speaker_id,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "success": True,
            "message": "Metadata API is running",
            "total_speakers": len(metadata_api.speakers_cache),
        }

    return app


# Create the app instance for uvicorn
app = create_app()


def main():
    """Run the development server"""

    print("Starting Spinorama Metadata Manager...")
    print("Open http://localhost:8005 in your browser")
    print("API endpoints available at http://localhost:8005/api/")
    print("API documentation at http://localhost:8005/docs")

    try:
        uvicorn.run("metadata_server:app", host="0.0.0.0", port=8005, reload=True, log_level="info")
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error starting server: {e}")


if __name__ == "__main__":
    main()
