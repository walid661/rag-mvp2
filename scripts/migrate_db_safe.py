import json
import re
import os

# Define paths
BASE_DIR = r"c:\Dossier Walid\rag-mvp2\data\processed\raw_v2\logic_jsonl_v2"
MESO_INPUT = os.path.join(BASE_DIR, "meso_catalog.jsonl")
MICRO_INPUT = os.path.join(BASE_DIR, "micro_catalog.jsonl")
MESO_OUTPUT = os.path.join(BASE_DIR, "meso_catalog_v2.jsonl")
MICRO_OUTPUT = os.path.join(BASE_DIR, "micro_catalog_v2.jsonl")

def parse_intensity(value):
    """Parses intensity string to integer percentage."""
    if not value:
        return None
    # Extract first number found
    match = re.search(r"(\d+)", str(value))
    if match:
        return int(match.group(1))
    return None

def parse_time(value):
    """Parses time string to total seconds."""
    if not value:
        return None
    
    # Normalize
    value = str(value).lower().strip()
    # First convert all curly single quotes to straight single quotes
    value = value.replace("’", "'").replace("‘", "'")
    # Convert all curly double quotes to straight double quotes
    value = value.replace("”", '"').replace("“", '"')
    # Convert two straight single quotes to one straight double quote
    value = value.replace("''", '"')
    
    # Handle ranges like "20-30" -> take the first number (min)
    # We want to process the string to get a single representative time first? 
    # Or parse the numbers and see the units.
    
    # Strategy: Look for Minutes ' Seconds " pattern first
    
    # Pattern: 1'30 or 1'30"
    match_min_sec = re.search(r"(\d+)'\s*(\d+)", value)
    if match_min_sec:
        minutes = int(match_min_sec.group(1))
        seconds = int(match_min_sec.group(2))
        return minutes * 60 + seconds
        
    # Pattern: 1' (minutes only)
    match_min = re.search(r"(\d+)'", value)
    if match_min and '"' not in value: # Ensure it's not 1'30" handled above (though regex above would catch it)
        # Check if it might be seconds denoted wrongly? 
        # But standard is ' = min.
        return int(match_min.group(1)) * 60
        
    # Pattern: 30" (seconds only)
    match_sec = re.search(r"(\d+)\"", value)
    if match_sec:
        return int(match_sec.group(1))
        
    # Fallback: just a number? "30" -> assume seconds usually
    # But if it says "1.5" -> could be minutes?
    # Let's look for simple integers.
    match_num = re.search(r"(\d+)", value)
    if match_num:
        return int(match_num.group(1))
        
    return None

def parse_sets(value):
    """Parses sets string to integer."""
    if not value:
        return None
    # "3-4" -> take min? or max? Let's take max to be safe for volume, or min for beginners.
    # Let's take the first number found.
    match = re.search(r"(\d+)", str(value))
    if match:
        return int(match.group(1))
    return None

def parse_reps(value):
    """Parses reps string to min/max range."""
    if not value:
        return None, None
    
    # "10-12"
    nums = re.findall(r"(\d+)", str(value))
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1])
    elif len(nums) == 1:
        return int(nums[0]), int(nums[0])
    return None, None

def transform_meso(data):
    """Transforms a single meso record."""
    variables = data.get("variables", {})
    constraints = {
        "intensity_pct": parse_intensity(variables.get("I")),
        "rest_sec": parse_time(variables.get("T")),
        "sets": parse_sets(variables.get("S")),
    }
    
    reps_min, reps_max = parse_reps(variables.get("RE"))
    if reps_min is not None:
        constraints["reps_min"] = reps_min
        constraints["reps_max"] = reps_max
        constraints["reps_target"] = reps_max # Default to max as target
        
    data["constraints"] = constraints
    return data

def extract_micro_structure(data):
    """Extracts structured data from micro text."""
    text = data.get("text", "").lower()
    structured = data.get("structured", {})
    if structured is None:
        structured = {}
        
    # Extract Equipment
    equipment = []
    if "poids du corps" in text or "autochargé" in text:
        equipment.append("bodyweight")
    if "élastique" in text or "bande" in text:
        equipment.append("resistance_band")
    if "haltères" in text:
        equipment.append("dumbbells")
    if "barre" in text:
        equipment.append("barbell")
    if "kettlebell" in text:
        equipment.append("kettlebell")
    if "machine" in text:
        equipment.append("machine")
        
    structured["equipment_detected"] = equipment
    
    # Extract Focus (simple keyword matching)
    focus = "general"
    if "hypertrophie" in text or "masse" in text:
        focus = "hypertrophy"
    elif "force" in text:
        focus = "strength"
    elif "endurance" in text or "cardio" in text:
        focus = "endurance"
    elif "mobilité" in text or "souplesse" in text:
        focus = "mobility"
    elif "puissance" in text or "explosif" in text:
        focus = "power"
        
    structured["focus_detected"] = focus
    
    # Extract Tempo
    # Look for patterns like "2-0-2" or "3-1-1"
    tempo_match = re.search(r"(\d-\d-\d(?:-\d)?)", data.get("variables", {}).get("RY", "") or text)
    if tempo_match:
        structured["tempo_detected"] = tempo_match.group(1)
    else:
        structured["tempo_detected"] = None

    data["structured"] = structured
    return data

def process_file(input_path, output_path, transformer):
    print(f"Processing {input_path} -> {output_path}")
    processed_count = 0
    examples = []
    
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            if not line.strip():
                continue
            
            try:
                original = json.loads(line)
                # Deep copy for comparison
                before = json.loads(line)
                
                transformed = transformer(original)
                
                outfile.write(json.dumps(transformed, ensure_ascii=False) + "\n")
                
                if processed_count < 3:
                    examples.append((before, transformed))
                
                processed_count += 1
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line[:50]}...")
                
    return examples

def main():
    print("Starting Migration...")
    
    # 1. Process Meso Catalog
    meso_examples = process_file(MESO_INPUT, MESO_OUTPUT, transform_meso)
    
    print("\n--- Meso Catalog Examples ---")
    for i, (before, after) in enumerate(meso_examples):
        print(f"\nExample {i+1}:")
        print(f"Before Variables: {before.get('variables')}")
        print(f"After Constraints: {after.get('constraints')}")

    # 2. Process Micro Catalog
    micro_examples = process_file(MICRO_INPUT, MICRO_OUTPUT, extract_micro_structure)
    
    print("\n--- Micro Catalog Examples ---")
    for i, (before, after) in enumerate(micro_examples):
        print(f"\nExample {i+1}:")
        print(f"Before Text: {before.get('text')[:100]}...")
        print(f"After Structured: {after.get('structured')}")

    print("\nMigration Completed Successfully.")

if __name__ == "__main__":
    main()
