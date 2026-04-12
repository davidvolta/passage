#!/usr/bin/env python3
"""Update notion words - runs as Railway cron job."""
import subprocess
import sys

def main():
    # Run ingest
    result = subprocess.run([sys.executable, "notion_ingest.py"], capture_output=True, text=True)
    print("Ingest output:", result.stdout)
    if result.returncode != 0:
        print("Ingest failed:", result.stderr)
        return 1

    # Generate words
    result = subprocess.run([sys.executable, "words.py", "--collection", "notion_words", "--count", "50"], capture_output=True, text=True)
    print("Words output:", result.stdout)
    if result.returncode != 0:
        print("Words generation failed:", result.stderr)
        return 1

    print("Notion words updated successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
