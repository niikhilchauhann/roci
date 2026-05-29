function cleanText(text) {
  return text
    ?.replace(/\s+/g, " ")
    ?.replace(/\n/g, " ")
    ?.trim();
}

function isReasonableRegistrationDate(value) {
  const text = cleanText(value);

  if (!text) {
    return false;
  }

  return /\b(19|20)\d{2}\b/.test(text);
}

export function validatePropertyRow(record) {
  const errors = [];

  if (!cleanText(record?.serial_no)) {
    errors.push("serial_no missing");
  }

  if (!cleanText(record?.registration_year)) {
    errors.push("registration_year missing");
  }

  if (!cleanText(record?.registration_no)) {
    errors.push("registration_no missing");
  }

  if (
    !isReasonableRegistrationDate(
      record?.registration_date
    )
  ) {
    errors.push("registration_date invalid");
  }

  if (!cleanText(record?.deed_type)) {
    errors.push("deed_type missing");
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
