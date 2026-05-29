import csv

from app.config import settings
from app.scrapers.bhunaksha import BhunakshaScraper


INPUT_FILE = settings.land_data_csv
OUTPUT_FILE = settings.parsed_land_data_csv


if __name__ == "__main__":
    scraper = BhunakshaScraper()
    parsed_rows = []

    with INPUT_FILE.open(mode="r", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            parsed = scraper.parse_plot_info(row["response_text"])
            parsed_rows.append(
                {
                    "plot_number": parsed["plot_number"],
                    "khata_number": parsed["khata_number"],
                    "owner_name": parsed["owner_name"],
                    "area": parsed["area"],
                }
            )
            print(f"Parsed Plot {parsed['plot_number']}")

    scraper.export_rows_to_csv(
        OUTPUT_FILE,
        ["plot_number", "khata_number", "owner_name", "area"],
        parsed_rows,
    )

    print("\nParsing Complete")
    print("Created:", OUTPUT_FILE)
