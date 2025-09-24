import os
import sys
from datetime import datetime, timedelta, timezone

# Add api modules to path to allow direct imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

from modules.nlp.entity_matcher import match_companies
from modules.nlp.categorizer import detect_category
from modules.nlp.event_extractor import extract_event
from modules.nlp.scoring import accuracy_pct, importance_pct, impact_level

def run():
    print("Running unit tests...")
    failures = 0

    # 1-1. Company Matching
    print("\n--- Testing Company Matching ---")
    text1 = "EU opens antitrust probe into NVIDIA; NVDA down 3%"
    matches1 = match_companies(text1, text1)
    if matches1 and matches1[0].name == 'NVIDIA' and matches1[0].confidence >= 0.8:
        print(f"PASS: '{text1}' -> Matched NVIDIA with confidence {matches1[0].confidence}")
    else:
        print(f"FAIL: '{text1}' -> Did not match NVIDIA correctly. Got: {matches1}")
        failures += 1

    text2 = "apple juice sales surge"
    matches2 = match_companies(text2, text2)
    if not matches2:
        print(f"PASS: '{text2}' -> No match as expected.")
    else:
        print(f"FAIL: '{text2}' -> Unexpectedly matched {matches2}")
        failures += 1

    # 1-2. Category/Event
    print("\n--- Testing Category & Event Extraction ---")
    text3 = "NVIDIA lowers Q3 guidance on supply"
    cat3 = detect_category(text3)
    evt3 = extract_event(text3)
    if cat3 == 'financials' and evt3 == 'guidance cut':
        print(f"PASS: '{text3}' -> Category: {cat3}, Event: {evt3}")
    else:
        print(f"FAIL: '{text3}' -> Expected financials/guidance cut, Got: {cat3}/{evt3}")
        failures += 1
        
    text4 = "EU launches antitrust investigation"
    cat4 = detect_category(text4)
    evt4 = extract_event(text4)
    if cat4 == 'regulation' and evt4 == 'antitrust probe':
        print(f"PASS: '{text4}' -> Category: {cat4}, Event: {evt4}")
    else:
        print(f"FAIL: '{text4}' -> Expected regulation/antitrust probe, Got: {cat4}/{evt4}")
        failures += 1

    # 1-3. Scoring
    print("\n--- Testing Scoring ---")
    acc = accuracy_pct('reuters.com')
    imp = importance_pct('regulation', -0.4, datetime.now(timezone.utc) - timedelta(hours=2), 0.92, 0.2)
    impact = impact_level(imp, 0.2)
    if acc >= 92 and imp >= 85 and impact == '큼':
         print(f"PASS: Reuters article -> Accuracy: {acc}, Importance: {imp}, Impact: {impact}")
    else:
        print(f"FAIL: Reuters article -> Expected acc>=92, imp>=85, impact='큼'. Got: acc={acc}, imp={imp}, impact={impact}")
        failures += 1

    print(f"\nTests finished. {failures} failures.")
    return failures

if __name__ == "__main__":
    os.environ['TEST_MODE'] = 'true'
    # Ensure DB is available for NLP modules that might need it
    print("NOTE: Some tests may require a running database connection.")
    run()
