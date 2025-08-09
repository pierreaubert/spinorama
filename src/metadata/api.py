#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metadata Management API for Spinorama
Handles CRUD operations for speaker metadata and Git integration
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import speakers_info from the datas module
try:
    from datas.metadata import speakers_info
except ImportError:
    # Fallback: try alternative import paths
    try:
        # Add project root to path
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from datas.metadata import speakers_info
    except ImportError:
        print("Warning: Could not import speakers_info, using empty dict")
        speakers_info = {}

# Define the types locally since we're in the datas directory
# Using direct type annotations instead of aliases to avoid conflicts


class MetadataAPI:
    """API for managing speaker metadata with Git integration"""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent.parent / "datas"
        else:
            self.data_dir = Path(data_dir)

        self.speakers_cache: Dict[str, Dict[str, Any]] = {}
        self.load_all_speakers()

    def load_all_speakers(self) -> None:
        """Load all speakers from centralized metadata"""
        self.speakers_cache.clear()

        # Load from the centralized speakers_info dictionary
        for speaker_key, speaker_data in speakers_info.items():
            # Explicit type annotation to resolve type checker conflict
            speaker_dict: Dict[str, Any] = dict(speaker_data)
            speaker_id = self._generate_speaker_id(
                speaker_dict.get("brand", ""), speaker_dict.get("model", "")
            )
            self.speakers_cache[speaker_id] = speaker_dict

    def _generate_speaker_id(self, brand: str, model: str) -> str:
        """Generate a consistent speaker ID from brand and model"""
        return f"{brand} {model}".lower().replace(" ", "-").replace("&", "and")

    def get_all_speakers(self) -> List[Dict[str, Any]]:
        """Get all speakers with their IDs"""
        speakers = []
        for speaker_id, speaker_data in self.speakers_cache.items():
            speaker_with_id = dict(speaker_data)
            speaker_with_id["id"] = speaker_id
            speakers.append(speaker_with_id)
        return speakers

    def get_speaker(self, speaker_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific speaker by ID"""
        speaker_data = self.speakers_cache.get(speaker_id)
        if speaker_data:
            speaker_with_id = dict(speaker_data)
            speaker_with_id["id"] = speaker_id
            return speaker_with_id
        return None

    def add_speaker(self, speaker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new speaker"""
        # Validate required fields
        required_fields = ["brand", "model", "type", "shape", "default_measurement", "measurements"]
        for field in required_fields:
            if field not in speaker_data:
                raise ValueError(f"Missing required field: {field}")

        speaker_id = self._generate_speaker_id(speaker_data["brand"], speaker_data["model"])

        # Check for duplicates
        if speaker_id in self.speakers_cache:
            raise ValueError(
                f"Speaker already exists: {speaker_data['brand']} {speaker_data['model']}"
            )

        # Add to cache
        self.speakers_cache[speaker_id] = speaker_data

        return {"id": speaker_id, "message": "Speaker added successfully"}

    def update_speaker(self, speaker_id: str, speaker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing speaker"""
        if speaker_id not in self.speakers_cache:
            raise ValueError(f"Speaker not found: {speaker_id}")

        # Validate required fields
        required_fields = ["brand", "model", "type", "shape"]
        for field in required_fields:
            if field not in speaker_data:
                raise ValueError(f"Missing required field: {field}")

        # Update cache
        self.speakers_cache[speaker_id] = speaker_data

        return {"id": speaker_id, "message": "Speaker updated successfully"}

    def delete_speaker(self, speaker_id: str) -> Dict[str, Any]:
        """Delete a speaker"""
        if speaker_id not in self.speakers_cache:
            raise ValueError(f"Speaker not found: {speaker_id}")

        del self.speakers_cache[speaker_id]

        return {"id": speaker_id, "message": "Speaker deleted successfully"}

    def export_changes(self, changes: List[tuple], commit_message: str) -> Dict[str, Any]:
        """Export changes to metadata files and create a Git branch"""
        try:
            # Create a new Git branch
            branch_name = f"metadata-update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            self._create_git_branch(branch_name)

            # Group changes by first letter of brand for file organization
            changes_by_letter = {}

            for speaker_id, change_info in changes:
                action = change_info["action"]

                if action in ["add", "edit"]:
                    speaker_data = change_info["data"]
                    first_letter = speaker_data["brand"][0].lower()

                    if first_letter not in changes_by_letter:
                        changes_by_letter[first_letter] = []

                    changes_by_letter[first_letter].append(
                        {"action": action, "speaker_id": speaker_id, "data": speaker_data}
                    )
                elif action == "delete":
                    # For deletions, we need to find which file contains the speaker
                    # This would require parsing existing files
                    pass

            # Update metadata files
            for letter, letter_changes in changes_by_letter.items():
                self._update_metadata_file(letter, letter_changes)

            # Commit changes
            self._commit_changes(commit_message)

            # Push branch and try to open a PR
            try:
                self._push_branch(branch_name)
                pr_url = self._create_pr_if_possible(branch_name, commit_message)
            except Exception:
                pr_url = None

            return {
                "success": True,
                "branch": branch_name,
                "pr_url": pr_url,
                "message": f"Changes exported to branch {branch_name}"
                + (f" (PR: {pr_url})" if pr_url else ""),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_git_branch(self, branch_name: str) -> None:
        """Create a new Git branch"""
        try:
            # Ensure we're in the right directory
            os.chdir(self.data_dir.parent.parent.parent)

            # Create and checkout new branch
            subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True)

        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create Git branch: {e.stderr.decode()}") from e

    def _update_metadata_file(self, letter: str, changes: List[Dict[str, Any]]) -> None:
        """Update a specific metadata file with changes"""
        metadata_file = self.data_dir / f"metadata_{letter}.py"

        # Read existing file or create new one
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = self._create_new_metadata_file_template(letter)

        # Parse and update the content
        updated_content = self._insert_speakers_into_file(content, changes, letter)

        # Write back to file
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(updated_content)

    def _create_new_metadata_file_template(self, letter: str) -> str:
        """Create a new metadata file template"""
        return f"""# -*- coding: utf-8 -*-
from . import SpeakerDatabase

speakers_info_{letter}: SpeakerDatabase = {{
}}
"""

    def _insert_speakers_into_file(
        self, content: str, changes: List[Dict[str, Any]], letter: str
    ) -> str:
        """Insert speaker data into the file content"""
        # Find the speakers_info dictionary
        pattern = rf"speakers_info_{letter}:\s*SpeakerDatabase\s*=\s*\{{"
        match = re.search(pattern, content)

        if not match:
            # If no existing dictionary found, create one
            return (
                content
                + f"\n\nspeakers_info_{letter}: SpeakerDatabase = {{\n{self._format_speakers(changes)}\n}}\n"
            )

        # Find the end of the dictionary
        start_pos = match.end()
        brace_count = 1
        pos = start_pos

        while pos < len(content) and brace_count > 0:
            if content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1

        if brace_count > 0:
            raise ValueError("Malformed metadata file: unmatched braces")

        # Insert new speakers before the closing brace
        insert_pos = pos - 1
        new_speakers = self._format_speakers(changes)

        # Check if we need a comma
        before_insert = content[:insert_pos].rstrip()
        if before_insert.endswith(",") or before_insert.endswith("{"):
            prefix = "\n" if not before_insert.endswith("{") else ""
        else:
            prefix = ",\n"

        updated_content = content[:insert_pos] + prefix + new_speakers + content[insert_pos:]

        return updated_content

    def _format_speakers(self, changes: List[Dict[str, Any]]) -> str:
        """Format speaker data as Python dictionary string (full serialization)"""

        def to_python_literal(data: Any, indent: int = 8) -> str:
            # Use JSON then map to Python literals
            txt = json.dumps(data, indent=indent, ensure_ascii=False)
            txt = txt.replace("true", "True").replace("false", "False").replace("null", "None")
            return txt

        formatted_speakers: List[str] = []
        for change in changes:
            if change["action"] in ["add", "edit"]:
                speaker_data: Dict[str, Any] = change["data"]
                # Remove transient keys
                speaker_copy = dict(speaker_data)
                speaker_copy.pop("id", None)
                speaker_key = f'"{speaker_copy.get("brand", "")} {speaker_copy.get("model", "")}"'

                # Build block: key: { full dict }
                py_dict = to_python_literal(speaker_copy, indent=8)
                indented = "\n".join("        " + line for line in py_dict.splitlines())
                formatted_speakers.append(f"    {speaker_key}: {indented}")

        return ",\n".join(formatted_speakers)

    def _push_branch(self, branch_name: str) -> None:
        """Push the branch to origin"""
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name], check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to push branch: {e.stderr.decode()}") from e

    def _create_pr_if_possible(self, branch_name: str, commit_message: str) -> Optional[str]:
        """Create a PR using GitHub CLI if available. Returns PR URL or None."""
        try:
            # Check gh availability
            chk = subprocess.run(["gh", "--version"], check=True, capture_output=True)
            if chk.returncode != 0:
                return None
            title = commit_message.strip() or f"Metadata update {branch_name}"
            body = "This PR was generated by the Metadata Manager. Please review the added/updated speaker metadata."
            pr = subprocess.run(
                ["gh", "pr", "create", "--fill", "-t", title, "-b", body, "-H", branch_name],
                check=True,
                capture_output=True,
            )
            # Try to get URL
            url = pr.stdout.decode().strip()
            return url if url else None
        except Exception:
            return None

    def _commit_changes(self, commit_message: str) -> None:
        """Commit the changes to Git"""
        try:
            # Add all changed metadata files
            subprocess.run(["git", "add", "datas/metadata_*.py"], check=True, capture_output=True)

            # Commit changes
            subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True)

        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to commit changes: {e.stderr.decode()}") from e

    def validate_speaker_data(self, speaker_data: Dict[str, Any]) -> List[str]:
        """Validate speaker data and return list of errors"""
        errors: List[str] = []

        # Required fields
        required_fields = ["brand", "model", "type", "shape"]
        for field in required_fields:
            if not speaker_data.get(field):
                errors.append(f"Missing required field: {field}")

        # Valid types
        valid_types = ["passive", "active"]
        if speaker_data.get("type") and speaker_data["type"] not in valid_types:
            errors.append(f"Invalid type: {speaker_data['type']}. Must be one of {valid_types}")

        # Valid shapes
        valid_shapes = [
            "floorstanders",
            "bookshelves",
            "center",
            "surround",
            "omnidirectional",
            "columns",
            "cbt",
            "outdoor",
            "panel",
            "inwall",
            "soundbar",
            "liveportable",
            "toursound",
            "cinema",
        ]
        if speaker_data.get("shape") and speaker_data["shape"] not in valid_shapes:
            errors.append(f"Invalid shape: {speaker_data['shape']}. Must be one of {valid_shapes}")

        # Validate measurements
        measurements = speaker_data.get("measurements", {})
        if not measurements:
            errors.append("At least one measurement is required")

        valid_formats = [
            "klippel",
            "webplotdigitizer",
            "spl_hv_txt",
            "gll_hv_txt",
            "princeton",
            "rew_text_dump",
        ]
        valid_qualities = ["low", "medium", "high", "unknown"]

        for meas_name, meas_data in measurements.items():
            if not meas_data.get("origin"):
                errors.append(f"Measurement '{meas_name}' missing origin")
            if not meas_data.get("format"):
                errors.append(f"Measurement '{meas_name}' missing format")
            elif meas_data["format"] not in valid_formats:
                errors.append(
                    f"Measurement '{meas_name}' has invalid format: {meas_data['format']}"
                )
            if meas_data.get("quality") and meas_data["quality"] not in valid_qualities:
                errors.append(
                    f"Measurement '{meas_name}' has invalid quality: {meas_data['quality']}"
                )

        return errors


if __name__ == "__main__":
    # Example usage
    api = MetadataAPI()

    # Test adding a speaker
    test_speaker = {
        "brand": "Test Brand",
        "model": "Test Model",
        "type": "active",
        "shape": "bookshelves",
        "price": "1000",
        "amount": "pair",
        "default_measurement": "test-measurement",
        "measurements": {
            "test-measurement": {"origin": "Test Origin", "format": "klippel", "quality": "high"}
        },
    }

    try:
        result = api.add_speaker(test_speaker)
        print("Added speaker:", result)

        # Test getting all speakers
        speakers = api.get_all_speakers()
        print(f"Total speakers: {len(speakers)}")

    except Exception as e:
        print("Error:", e)
