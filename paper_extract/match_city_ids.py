#!/usr/bin/env python3
"""
Match CCAS system regions to formalized cities and write city_id.

Default behavior updates:
  - output/paper_to_ccas_systems.csv
using:
  - output/cities.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class City:
    city_id: str
    city_slug: str
    name: str
    country_code: str
    normalized_name: str


GENERIC_OR_NON_CITY_REGIONS = {
    "no systems found",
    "unknown",
    "n a",
    "turkey",
    "chile",
    "croatia",
    "sweden",
    "united states",
    "ghana",
    "brazil",
    "germany",
    "spain",
    "hungary",
    "china",
    "sri lanka",
    "england",
    "norway",
    "tunisia",
    "kenya",
    "romania",
    "singapore",
    "mexico",
    "israel",
    "japan",
    "afghanistan",
    "belgium",
    "netherlands",
    "oecd countries",
    "south korea",
    "district of columbia",
    "trinidad and tobago",
    "barbados",
    "victoria",
    "flanders",
    "inner mongolia",
    "chhattisgarh",
    "colorado",
    "minnesota",
    "denmark",
    "iran",
    "portugal",
    "hong kong",
}

# Used when region strings are known aliases or include a district format.
ALIAS_TO_CITY_SLUG = {
    "tel aviv": "isr-tel-aviv-yafo",
    "staten island": "usa-staten-island",
    "washington dc": "usa-washington-dc",
    "charlotte mecklenburg": "usa-charlotte",
    "new york city": "us-new-york-city",
    "new york": "usa-new-york",
    "boston": "usa-boston",
    "chicago": "usa-chicago",
    "denver": "usa-denver",
    "new haven": "usa-new-haven",
    "cambridge": "usa-cambridge",
    "seattle": "usa-seattle",
    "new orleans": "usa-new-orleans",
    "newark": "usa-newark",
    "columbus": "usa-columbus",
    "minneapolis": "usa-minneapolis",
    "mexico city": "mex-mexico-city",
}


def normalize_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value or "").encode(
        "ascii", "ignore"
    ).decode("ascii")
    cleaned = ascii_value.lower().replace("&", " and ")
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def load_cities(cities_csv_path: Path) -> tuple[list[City], dict[str, str]]:
    cities: list[City] = []
    slug_to_id: dict[str, str] = {}

    with cities_csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter=";")
        for row in reader:
            city_id = (row.get("id") or "").strip()
            city_slug = (row.get("city_id_slug") or "").strip()
            city_name = (row.get("name") or "").strip()
            country_code = (row.get("country_code") or "").strip()

            if not city_id or not city_name:
                continue

            city = City(
                city_id=city_id,
                city_slug=city_slug,
                name=city_name,
                country_code=country_code,
                normalized_name=normalize_text(city_name),
            )
            cities.append(city)

            if city_slug:
                slug_to_id[city_slug] = city_id

    # Prefer longer name matches (e.g., "new york city" before "new york").
    cities.sort(key=lambda city: len(city.normalized_name), reverse=True)
    return cities, slug_to_id


def choose_city_id(
    region: str,
    iso3_country_code: str,
    cities: list[City],
    slug_to_id: dict[str, str],
) -> str:
    normalized_region = normalize_text(region)
    if not normalized_region or normalized_region in GENERIC_OR_NON_CITY_REGIONS:
        return ""

    for alias, city_slug in ALIAS_TO_CITY_SLUG.items():
        if alias in normalized_region:
            city_id = slug_to_id.get(city_slug, "")
            if city_id:
                return city_id

    candidates: list[City] = []
    for city in cities:
        if (
            iso3_country_code
            and iso3_country_code not in {"Unknown", "N/A"}
            and city.country_code
            and city.country_code != iso3_country_code
        ):
            continue
        if city.normalized_name and city.normalized_name in normalized_region:
            candidates.append(city)

    if candidates and "new york city" in normalized_region:
        candidates = [
            city for city in candidates if city.normalized_name != "new york"
        ]

    if not candidates:
        return ""

    unique_candidates = {(city.normalized_name, city.country_code) for city in candidates}
    if len(unique_candidates) == 1:
        return candidates[0].city_id

    # Multi-city expressions should remain blank.
    if " and " in normalized_region or "-" in region or "/" in region:
        return ""

    return candidates[0].city_id


def update_paper_to_ccas(
    systems_csv_path: Path,
    cities: list[City],
    slug_to_id: dict[str, str],
) -> tuple[int, int]:
    with systems_csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "city_id" not in fieldnames:
        fieldnames.append("city_id")

    matched = 0
    for row in rows:
        region = (row.get("region") or "").strip()
        iso3_country_code = (row.get("iso3_country_code") or "").strip()
        city_id = choose_city_id(region, iso3_country_code, cities, slug_to_id)
        row["city_id"] = city_id
        if city_id:
            matched += 1

    with systems_csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows), matched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate city_id in paper_to_ccas_systems.csv using cities.csv."
    )
    parser.add_argument(
        "--systems-csv",
        type=Path,
        default=Path("output/paper_to_ccas_systems.csv"),
        help="Path to paper_to_ccas_systems CSV (default: output/paper_to_ccas_systems.csv).",
    )
    parser.add_argument(
        "--cities-csv",
        type=Path,
        default=Path("output/cities.csv"),
        help="Path to cities CSV (default: output/cities.csv).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cities, slug_to_id = load_cities(args.cities_csv)
    total_rows, matched_rows = update_paper_to_ccas(args.systems_csv, cities, slug_to_id)
    print(f"Updated {args.systems_csv} ({matched_rows}/{total_rows} rows matched).")


if __name__ == "__main__":
    main()
