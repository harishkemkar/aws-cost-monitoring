import subprocess
import json
import datetime
import os

def load_settings():
    """Load threshold and other settings from config/settings.json"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.json")
    try:
        with open(config_path, "r") as f:
            settings = json.load(f)
        return settings.get("threshold", 10.0)  # default to 10 if not set
    except Exception as e:
        print(f"Error loading settings.json: {e}")
        return 10.0

def get_month_dates():
    today = datetime.date.today()
    start_of_month = today.replace(day=1)
    end_date = today + datetime.timedelta(days=1)
    month_name = start_of_month.strftime("%B %Y")
    return start_of_month.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), month_name

def run_aws_cost_explorer(start_date, end_date):
    cmd = [
        "aws", "ce", "get-cost-and-usage",
        "--time-period", f"Start={start_date},End={end_date}",
        "--granularity", "DAILY",
        "--metrics", "UnblendedCost"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Error running AWS CLI: {result.stderr}")
    return json.loads(result.stdout)

def print_full_report(data, month_label):
    results = data.get("ResultsByTime", [])
    if not results:
        print("No data found for this period.")
        return 0.0

    print(f"--- AWS Usage Report for {month_label} ---\n")

    weekly_total = 0.0
    month_total = 0.0
    week_start = results[0]["TimePeriod"]["Start"]

    for i, entry in enumerate(results):
        day_start = entry["TimePeriod"]["Start"]
        day_end = entry["TimePeriod"]["End"]
        amount_str = entry["Total"]["UnblendedCost"]["Amount"]
        amount_float = float(amount_str)
        unit = entry["Total"]["UnblendedCost"]["Unit"]

        # Print daily usage
        print(f"{day_start} → {day_end}: {amount_str} {unit}")

        weekly_total += amount_float
        month_total += amount_float

        # End of week or last record
        if (i + 1) % 7 == 0 or (i + 1) == len(results):
            week_number = ((i + 1) // 7) if (i + 1) % 7 == 0 else ((i + 1) // 7) + 1
            print(f"\n>> WEEK {week_number} SUMMARY ({week_start} to {day_end})")
            print(f">> Total: {weekly_total:.2f} {unit}\n" + "-"*40)
            if (i + 1) < len(results):
                week_start = results[i + 1]["TimePeriod"]["Start"]
            weekly_total = 0.0

    return month_total

def trigger_delete():
    print("Threshold exceeded. Running delete script...")
    subprocess.run(["python", "scripts\\aws_cleanup.py"])  # adjust path if needed

def main():
    threshold = load_settings()
    print(f"Threshold set to: {threshold} USD\n")

    start_date, end_date, month_label = get_month_dates()
    data = run_aws_cost_explorer(start_date, end_date)
    month_total = print_full_report(data, month_label)

    print(f"\n>>> Monthly Total So Far: {month_total:.2f} USD <<<\n")

    if month_total > threshold:
        trigger_delete()
    else:
        print("Usage within limit. No action taken.")

if __name__ == "__main__":
    main()