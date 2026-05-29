import fs from "fs";

const EXPORT_COLUMNS = [
  "serial_no",
  "registration_year",
  "registration_no",
  "party_name",
  "address",
  "property_details",
  "khasra",
  "registration_date",
  "deed_type",
  "action",
];

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 60);
}

function escapeCSVValue(value) {
  const text = String(value ?? "");
  const escaped = text.replace(/"/g, '""');
  return `"${escaped}"`;
}

export function createExportBaseName({
  villageName,
  villageCode,
  propertyId,
  propertyAddress,
}) {
  const locationPart =
    slugify(villageName) ||
    `village_${slugify(villageCode) || "unknown"}`;

  const propertyPart =
    slugify(propertyId) ||
    slugify(propertyAddress) ||
    "property";

  return `igrsup_transactions_${locationPart}_plot_${propertyPart}`;
}

export function exportTransactionsJSON(filePath, rows) {
  fs.writeFileSync(
    filePath,
    JSON.stringify(rows, null, 2),
    "utf-8"
  );
}

export function exportTransactionsCSV(filePath, rows) {
  const header = EXPORT_COLUMNS.join(",");
  const body = rows.map(row =>
    EXPORT_COLUMNS.map(column =>
      escapeCSVValue(row[column])
    ).join(",")
  );

  const csvContent =
    `\uFEFF${[header, ...body].join("\n")}\n`;

  fs.writeFileSync(
    filePath,
    csvContent,
    "utf-8"
  );
}

export function exportTransactions(baseFilePath, rows) {
  fs.mkdirSync(
    filePathDirectory(baseFilePath),
    { recursive: true }
  );

  exportTransactionsJSON(
    `${baseFilePath}.json`,
    rows
  );

  exportTransactionsCSV(
    `${baseFilePath}.csv`,
    rows
  );

  return {
    jsonPath: `${baseFilePath}.json`,
    csvPath: `${baseFilePath}.csv`,
  };
}

function filePathDirectory(filePath) {
  const normalized =
    filePath.replace(/\\/g, "/");

  const lastSlashIndex =
    normalized.lastIndexOf("/");

  if (lastSlashIndex === -1) {
    return ".";
  }

  return normalized.slice(0, lastSlashIndex);
}
