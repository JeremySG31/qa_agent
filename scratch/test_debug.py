import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agent import planner
from agent import executor

prompt = "open https://es.wikipedia.org/"
try:
    steps = planner.generate_test_plan(prompt)
    print(f"Steps: {steps}")
    result = executor.run_test("Test Wikipedia", steps, headless=True)
    print(f"Result: {result['status']}")
    if result['error']:
        print(f"Error: {result['error']}")
except Exception as e:
    print(f"Exception: {e}")
