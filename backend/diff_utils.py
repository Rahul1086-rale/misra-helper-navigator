# diff_utils.py - Utility functions for creating diffs between original and fixed files

import os
import tempfile
import re
from typing import Tuple, Optional, List
from denumbering import remove_line_numbers
from replace import merge_fixed_snippets_into_file

def create_temp_fixed_denumbered_file(
    numbered_file_path: str, 
    fixed_snippets: dict, 
    project_id: str,
    upload_folder: str = "uploads"
) -> Tuple[str, str]:
    """
    Create a temporary fixed and denumbered file for diff comparison.
    
    Args:
        numbered_file_path: Path to the numbered file
        fixed_snippets: Dictionary of fixed code snippets
        project_id: Project identifier
        upload_folder: Upload folder path
        
    Returns:
        Tuple of (temp_fixed_numbered_path, temp_fixed_denumbered_path)
    """
    
    # Create temporary fixed numbered file
    temp_fixed_numbered_path = os.path.join(
        upload_folder, 
        f"{project_id}_temp_fixed_numbered.cpp"
    )
    
    # Apply fixes to create temp fixed numbered file
    merge_fixed_snippets_into_file(
        numbered_file_path, 
        fixed_snippets, 
        temp_fixed_numbered_path
    )
    
    # Create temporary fixed denumbered file
    temp_fixed_denumbered_path = os.path.join(
        upload_folder, 
        f"{project_id}_temp_fixed_denumbered.cpp"
    )
    
    # Remove line numbers from the fixed file
    remove_line_numbers(temp_fixed_numbered_path, temp_fixed_denumbered_path)
    
    return temp_fixed_numbered_path, temp_fixed_denumbered_path

def get_file_content(file_path: str) -> Optional[str]:
    """
    Read and return file content as string.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File content as string or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

def create_diff_data(original_file_path: str, fixed_file_path: str, fixed_snippets: dict = None) -> dict:
    """
    Create diff data structure for frontend consumption.
    
    Args:
        original_file_path: Path to original file
        fixed_file_path: Path to fixed file
        fixed_snippets: Dictionary of fixed code snippets
        
    Returns:
        Dictionary containing diff data
    """
    original_content = get_file_content(original_file_path)
    fixed_content = get_file_content(fixed_file_path)
    
    # Extract line numbers to highlight if fixed_snippets provided
    highlight_data = {}
    if fixed_snippets:
        try:
            original_lines, fixed_lines = get_original_and_fixed_lines(fixed_snippets)
            highlight_data = {
                "original_lines": original_lines,
                "fixed_lines": fixed_lines
            }
        except Exception as e:
            print(f"Error extracting highlight lines: {str(e)}")
            highlight_data = {"original_lines": [], "fixed_lines": []}
    
    return {
        "original": original_content or "",
        "fixed": fixed_content or "",
        "has_changes": original_content != fixed_content if original_content and fixed_content else False,
        "highlight": highlight_data
    }

def get_original_and_fixed_lines(json_data):
    """
    Extract original and fixed line numbers from JSON data.
    
    Args:
        json_data: Dictionary mapping line keys to content
        
    Returns:
        Tuple of (original_lines, fixed_lines) - lists of line numbers to highlight
    """
    original_lines = []
    fixed_line_map = {}
    inserted_count = 0

    sorted_keys = sorted(json_data.keys(), key=lambda k: (int(re.match(r'\d+', k).group()), k))

    for key in sorted_keys:
        base_line = int(re.match(r'\d+', key).group())

        if key.isdigit():
            original_lines.append(base_line)

        if re.search(r'[a-z]$', key):
            inserted_count += 1
            fixed_line_map[key] = base_line + inserted_count
        else:
            fixed_line_map[key] = base_line + inserted_count

    # Return only the mapped line numbers
    fixed_lines = sorted(set(fixed_line_map.values()))
    return sorted(set(original_lines)), fixed_lines

def cleanup_temp_files(*file_paths: str) -> None:
    """
    Clean up temporary files.
    
    Args:
        file_paths: Variable number of file paths to clean up
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {str(e)}")