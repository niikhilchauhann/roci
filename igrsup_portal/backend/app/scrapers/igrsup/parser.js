import * as cheerio from "cheerio";

import { IGRSUP_SELECTORS } from "./selectors.js";
import { hasMeaningfulRowData, validatePropertyRow } from "./validator.js";

export function cleanText(text) {
  return text
    ?.replace(/\s+/g, " ")
    ?.replace(/\n/g, " ")
    ?.trim();
}

function isHeaderRow(cells) {
  const firstCell = cells[0]?.toLowerCase();

  return (
    firstCell?.includes("क्र.सं") ||
    firstCell === "serial no" ||
    firstCell === "sr. no."
  );
}

function mapPropertyRow(cells) {
  return {
    serial_no: cells[0],
    registration_year: cells[1],
    registration_no: cells[2],
    party_name: cells[3],
    address: cells[4],
    property_details: cells[5],
    khasra: cells[6],
    registration_date: cells[7],
    deed_type: cells[8],
    action: cells[9],
  };
}

export function parseIGRSUPPropertyTable(html) {
  const $ = cheerio.load(html);
  const rows = [];

  $(IGRSUP_SELECTORS.resultRows).each((index, row) => {
    const tds = $(row).find("td");
    const cells = tds
      .map((i, el) => cleanText($(el).text()))
      .get();

    console.log("TD COUNT:", tds.length);
    console.log(cells);

    if (tds.length < 10) {
      return;
    }

    if (!hasMeaningfulRowData(cells)) {
      return;
    }

    if (isHeaderRow(cells)) {
      return;
    }

    const validation = validatePropertyRow(cells);

    if (!validation.isValid) {
      return;
    }

    rows.push(mapPropertyRow(validation.cleanedCells));
  });

  return rows;
}
