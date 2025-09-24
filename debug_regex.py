import json, re, os, sys

rules_path = os.path.join(os.getcwd(), "api", "data", "rules", "category_event_rules.json")
test_text = "NVIDIA lowers Q3 guidance on supply"

try:
    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)
    
    event_regexes = rules.get("EVENT_REGEX", {})
    guidance_cut_patterns = event_regexes.get("guidance cut", [])
    
    sys.stdout.write("Test Text: {}\n".format(test_text))
    sys.stdout.write("Guidance Cut Patterns: {}\n".format(guidance_cut_patterns))
    
    matched = False
    for pattern in guidance_cut_patterns:
        if re.search(pattern, test_text, flags=re.I):
            sys.stdout.write("MATCH FOUND with pattern: {}\n".format(pattern))
            matched = True
            break
    
    if not matched:
        sys.stdout.write("NO MATCH FOUND for 'guidance cut' event.\n")

except FileNotFoundError:
    sys.stdout.write("Error: Rules file not found at {}\n".format(rules_path))
except json.JSONDecodeError:
    sys.stdout.write("Error: Could not decode JSON from {}\n".format(rules_path))
except Exception as e:
    sys.stdout.write("An unexpected error occurred: {}\n".format(e))

sys.stdout.flush()
