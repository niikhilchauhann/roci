import * as cheerio from "cheerio";
import { validatePropertyRow } from "./validator.js";

function cleanText(text) {
  return text
    ?.replace(/\s+/g, " ")
    ?.replace(/\n/g, " ")
    ?.trim();
}

export function parsePropertyHTML(html) {
  const $ = cheerio.load(html);

  const rows = [];

  $("table#tablepaging tr").each((index, row) => {
    // IMPORTANT:
    // only direct td children
    // prevents nested table issues
    const tds = $(row).children("td");

    // skip invalid rows
    if (tds.length < 10) {
      return;
    }

    const cols = tds
      .map((i, el) =>
        cleanText($(el).text())
      )
      .get();

    console.log(
      "VALID TD COUNT:",
      tds.length
    );

    console.log(
      "VALID ROW:",
      cols
    );

    // skip empty rows
    const hasMeaningfulData =
      cols.some(value => value);

    if (!hasMeaningfulData) {
      return;
    }

    // skip header rows
    if (
      cols[0]?.includes("क्र.सं") ||
      cols[0]
        ?.toLowerCase()
        ?.includes("serial")
    ) {
      return;
    }

    const record = {
      serial_no: cols[0],
      registration_year: cols[1],
      registration_no: cols[2],
      party_name: cols[3],
      address: cols[4],
      property_details: cols[5],
      khasra: cols[6],
      registration_date: cols[7],
      deed_type: cols[8],
      action: cols[9],
    };

    const validation =
      validatePropertyRow(record);

    if (!validation.valid) {
      console.log(
        "INVALID ROW:",
        validation.errors
      );

      return;
    }

    rows.push(record);
  });

  return rows;
}
