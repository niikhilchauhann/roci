function cleanText(text) {
  return text
    ?.replace(/\s+/g, " ")
    ?.replace(/\n/g, " ")
    ?.trim();
}

export function isValidRegistrationYear(value) {
  const text = cleanText(value);

  if (!text) {
    return false;
  }

  return /^\d{4}$/.test(text);
}

export function hasRegistrationNumber(value) {
  return Boolean(cleanText(value));
}

export function isReasonableRegistrationDate(value) {
  const text = cleanText(value);

  if (!text) {
    return false;
  }

  return /^(0?[1-9]|[12][0-9]|3[01])[\/.-](0?[1-9]|1[0-2])[\/.-](\d{2}|\d{4})$/.test(
    text
  );
}

export function hasMeaningfulRowData(cells) {
  return cells.some(value => Boolean(cleanText(value)));
}

export function validatePropertyRow(cells) {
  const cleanedCells = cells.map(value => cleanText(value));
  const errors = [];

  if (cleanedCells.length < 10) {
    errors.push("td count < 10");
  }

  if (!hasMeaningfulRowData(cleanedCells)) {
    errors.push("row has no meaningful data");
  }

  if (!isValidRegistrationYear(cleanedCells[1])) {
    errors.push("registration_year invalid");
  }

  if (!hasRegistrationNumber(cleanedCells[2])) {
    errors.push("registration_no missing");
  }

  if (!isReasonableRegistrationDate(cleanedCells[7])) {
    errors.push("registration_date invalid");
  }

  return {
    isValid: errors.length === 0,
    errors,
    cleanedCells,
  };
}
