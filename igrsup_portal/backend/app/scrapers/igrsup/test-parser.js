import fs from "fs";

import { saveJSON } from "./exporter.js";
import { parseIGRSUPPropertyTable } from "./parser.js";

const inputPath =
  "./data/raw/property-search-result.html";

const outputPath =
  "./data/parsed_land_data.json";

const html = fs.readFileSync(
  inputPath,
  "utf-8"
);

const rows =
  parseIGRSUPPropertyTable(html);

console.log(
  JSON.stringify(rows, null, 2)
);

saveJSON(outputPath, rows);

console.log(
  `Parsed ${rows.length} records successfully`
);
