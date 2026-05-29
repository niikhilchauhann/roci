import fs from "fs";

import { parsePropertyHTML } from
  "../modules/igrsup/property/parser.js";

// LOAD HTML
const html = fs.readFileSync(
  "./data/raw/property-response.html",
  "utf-8"
);

// PARSE
const rows = parsePropertyHTML(html);

// SHOW
console.log(
  JSON.stringify(rows, null, 2)
);

// SAVE
fs.writeFileSync(
  "./data/parsed_land_data.json",
  JSON.stringify(rows, null, 2)
);

console.log(
  `Parsed ${rows.length} records successfully`
);