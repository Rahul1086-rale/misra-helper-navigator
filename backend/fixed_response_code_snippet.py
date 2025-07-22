# fixed_response_code_snippet.py
import re
import json

def extract_snippets_from_response(response_text):
    """
    Parses Gemini-style C++ response text and extracts line-numbered code,
    preserving backslashes and formatting. Returns a dictionary.
    """
    print(f"🔍 Processing response text of length: {len(response_text)}")
    
    # Match all ```cpp ... ``` blocks (non-greedy)
    code_blocks = re.findall(r"```(?:cpp|c\+\+)?\s*\n(.*?)```", response_text, re.DOTALL)
    print(f"📝 Found {len(code_blocks)} code blocks")
    
    all_lines = {}

    for i, block in enumerate(code_blocks):
        print(f"🔧 Processing block {i+1}:")
        lines = block.strip().splitlines()
        print(f"   Lines in block: {len(lines)}")
        
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Try multiple patterns for line numbers
            patterns = [
                r"^(\d+[a-zA-Z]*):(.*)$",           # 123: code
                r"^(\d+[a-zA-Z]*)\s+(.*)$",         # 123 code
                r"^(\d+[a-zA-Z]*)\.\s*(.*)$",       # 123. code
                r"^(\d+[a-zA-Z]*)\)\s*(.*)$",       # 123) code
            ]
            
            matched = False
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    lineno = match.group(1).strip()
                    code = match.group(2).rstrip()  # Do NOT strip backslashes
                    all_lines[lineno] = code
                    matched = True
                    print(f"   ✅ Extracted line {lineno}: {code[:50]}...")
                    break
            
            if not matched:
                print(f"   ⚠️ Skipping line {line_idx+1}: {line[:100]}...")
    
    print(f"🎯 Total extracted lines: {len(all_lines)}")
    return all_lines


def save_snippets_to_json(snippets, filepath="temp_snippets.json"):
    with open(filepath, "w") as f:
        json.dump(snippets, f, indent=2)