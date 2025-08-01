# === Parses data from the rated_disabilities API call at va.gov ===
# === Visit the below URL after logging in to va.gov to retrieve json data ===
# === https://api.va.gov/v0/rated_disabilities ===

import json
import questionary
from tabulate import tabulate

# === Load JSON from a file ===
file_path = input("Enter the path to your JSON file: ").strip()
try:
    with open(file_path, "r") as f:
        json_data = json.load(f)
except Exception as e:
    print(f"[Error] Could not read file: {e}")
    exit(1)

# === Interactive filter menu using questionary ===
def get_user_filters():
    while True:
        answers = questionary.checkbox(
            "Select condition filters (use space to select, enter to confirm):",
            choices=[
                questionary.Choice("0. All conditions (no filtering)", value="0"),
                questionary.Choice("1. Service Connected only", value="1"),
                questionary.Choice("2. Not Service Connected only", value="2"),
                questionary.Choice("3. Static only", value="3"),
                questionary.Choice("4. Non-Static only", value="4"),
            ]
        ).ask()

        if answers is None:
            print("No filters selected. Exiting.")
            exit(0)

        selected_filters = set(answers)

        # Validate conflicts
        if {"1", "2"}.issubset(selected_filters):
            print("[Error] Cannot select both 'Service Connected' and 'Not Service Connected'.\n")
        elif {"3", "4"}.issubset(selected_filters):
            print("[Error] Cannot select both 'Static' and 'Non-Static'.\n")
        elif "0" in selected_filters and len(selected_filters) > 1:
            print("[Error] 'All conditions' cannot be combined with other filters.\n")
        else:
            return selected_filters

# === Extract individual ratings ===
try:
    ratings = json_data["data"]["attributes"]["individual_ratings"]
except KeyError:
    print("[Error] Invalid JSON structure. Missing 'individual_ratings'.")
    exit(1)

# === Get filters from user ===
selected_filters = get_user_filters()

# === Filtering logic ===
def rating_matches_filters(rating):
    if "0" in selected_filters:
        return True
    checks = {
        "1": rating.get("decision") == "Service Connected",
        "2": rating.get("decision") == "Not Service Connected",
        "3": rating.get("static_ind") is True,
        "4": rating.get("static_ind") is False,
    }
    return all(checks[choice] for choice in selected_filters if choice in checks)

# === Apply filtering and extract output fields ===
filtered = []
for r in ratings:
    if rating_matches_filters(r):
        filtered.append({
            "Decision": r.get("decision"),
            "Rating %": r.get("rating_percentage"),
            "Condition": r.get("diagnostic_type_name"),
            "Description": r.get("diagnostic_text"),
            "Static": r.get("static_ind")
        })

# === Sort: Service Connected first, Not Service Connected last; within group, rating % desc ===
def sort_key(entry):
    conn_rank = 1 if entry["Decision"] == "Not Service Connected" else 0
    rating_pct = entry["Rating %"] or 0
    return (conn_rank, -rating_pct)

filtered.sort(key=sort_key)

# === Display results ===
if filtered:
    table = tabulate(filtered, headers="keys", tablefmt="grid")
    print("\nFiltered Results (Service Connected first, Not Service Connected last, sorted by rating % descending):\n")
    print(table)

    # Prompt to save output to file
    save_to_file = questionary.confirm("Do you want to save the results to a file?").ask()
    if save_to_file:
        filename = questionary.text("Enter filename to save results:", default="results.txt").ask()
        try:
            with open(filename, "w") as f:
                f.write(table)
            print(f"\n[✔] Results saved to {filename}")
        except Exception as e:
            print(f"[Error] Could not write to file: {e}")
else:
    print("\nNo results matched your criteria.")
