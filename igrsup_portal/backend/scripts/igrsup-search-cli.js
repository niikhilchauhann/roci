#!/usr/bin/env node
/**
 * CLI wrapper around searchProperty — called by the Python IgrsupAdapter.
 * Reads params from env vars, writes a single JSON line to stdout.
 *
 * Required env vars:
 *   IGRSUP_SESSION_PATH   absolute path to igrsup-session.json
 *   IGRSUP_DISTRICT_CODE
 *   IGRSUP_SRO_CODE
 *
 * Optional env vars:
 *   IGRSUP_VILLAGE_CODE   leave blank for tehsil-wide search (recommended)
 *   IGRSUP_PROPERTY_ID    gatta/khasra number; leave blank to match all
 *   IGRSUP_PROPERTY_ADDR  address text; defaults to IGRSUP_PROPERTY_ID
 *   IGRSUP_YEAR_CURRENT   4-digit year for n_current count (default: current year)
 *   IGRSUP_YEAR_PREVIOUS  4-digit year for n_previous count (default: current year - 1)
 */

import { searchProperty } from "../modules/igrsup/property/search.js";

const sessionPath = process.env.IGRSUP_SESSION_PATH;
const districtCode = process.env.IGRSUP_DISTRICT_CODE;
const sroCode = process.env.IGRSUP_SRO_CODE;
const villageCode = process.env.IGRSUP_VILLAGE_CODE ?? "";
const propertyId = process.env.IGRSUP_PROPERTY_ID ?? "";
const propertyAddress = process.env.IGRSUP_PROPERTY_ADDR ?? propertyId;

const thisYear = new Date().getFullYear();
const yearCurrent = process.env.IGRSUP_YEAR_CURRENT
  ? parseInt(process.env.IGRSUP_YEAR_CURRENT, 10)
  : thisYear;
const yearPrevious = process.env.IGRSUP_YEAR_PREVIOUS
  ? parseInt(process.env.IGRSUP_YEAR_PREVIOUS, 10)
  : thisYear - 1;

if (!sessionPath || !districtCode || !sroCode) {
  process.stderr.write(
    JSON.stringify({
      error:
        "Missing required env vars: IGRSUP_SESSION_PATH, IGRSUP_DISTRICT_CODE, IGRSUP_SRO_CODE",
    }) + "\n"
  );
  process.exit(1);
}

async function main() {
  try {
    const allRecords = await searchProperty({
      districtCode,
      sroCode,
      villageCode,
      propertyId,
      propertyAddress,
    });

    // Filter by registration year client-side
    const currentRecords = allRecords.filter(
      (r) => r.registration_year === String(yearCurrent)
    );
    const previousRecords = allRecords.filter(
      (r) => r.registration_year === String(yearPrevious)
    );

    const result = {
      status: "ok",
      n_current: currentRecords.length,
      n_previous: previousRecords.length,
      year_current: yearCurrent,
      year_previous: yearPrevious,
      total_records: allRecords.length,
      // Include a sample of current-year records for debugging
      sample_records: currentRecords.slice(0, 10),
    };

    process.stdout.write(JSON.stringify(result) + "\n");
  } catch (err) {
    process.stderr.write(
      JSON.stringify({ error: String(err?.message ?? err) }) + "\n"
    );
    process.exit(1);
  }
}

main();
