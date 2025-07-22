# diff_utils.py - Utility functions for creating diffs between original and fixed files

import os
import tempfile
from typing import Tuple, Optional
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

def create_diff_data(original_file_path: str, fixed_file_path: str) -> dict:
    """
    Create diff data structure for frontend consumption.
    
    Args:
        original_file_path: Path to original file
        fixed_file_path: Path to fixed file
        
    Returns:
        Dictionary containing diff data
    """
    original_content = get_file_content(original_file_path)
    fixed_content = get_file_content(fixed_file_path)
    
    return {
        "original": original_content or "",
        "fixed": fixed_content or "",
        "has_changes": original_content != fixed_content if original_content and fixed_content else False
    }

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