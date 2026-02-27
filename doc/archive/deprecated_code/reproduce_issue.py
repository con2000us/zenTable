
import json
import os

data = [
    {"Name": "Green Circle", "Emoji": "🟢", "Status": "Active"},
    {"Name": "Red Circle", "Emoji": "🔴", "Status": "Error"},
    {"Name": "Party Popper", "Emoji": "🎉", "Status": "Celebration"},
    {"Name": "Rocket", "Emoji": "🚀", "Status": "Launch"},
    {"Name": "Complex", "Emoji": "👨‍👩‍👧‍👦", "Status": "Family"},
    {"Name": "Flag", "Emoji": "🇹🇼", "Status": "Taiwan"}
]

with open("issue_repro.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Created issue_repro.json")
