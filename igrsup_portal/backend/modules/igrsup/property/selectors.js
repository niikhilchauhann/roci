export const PROPERTY_SELECTORS = {
  searchPage:
    "https://igrsup.gov.in/igrsup/us_newPropertySearchAction",

  form: "form",

  // ── Dropdowns (the form uses <select>, NOT <input>) ──
  districtSelect:  'select[name="districtCode"]',
  sroSelect:       'select[name="sroCode"]',
  villageSelect:   'select[name="gaonCode1"]',

  // ── Text inputs ──
  propertyIdInput:
    'input[type="text"], textarea',
  propertyAddressInput:
    'input[type="text"], textarea',

  // ── Submit ──
  submitButton:
    'input[type="submit"], button[type="submit"], a[onclick*="submit"]',
  propertyDeedButton:
    'text=/.*Property Deed.*/i',
  propertyDeedButtonHindi:
    'text=/.*सम्पत्ति लिखित विवरण.*/i',
  propertyDeedButtonGeneric:
    'td:has-text("Property Deed")',

  // ── Results ──
  resultTable: "table#tablepaging",
  resultRows:  "table#tablepaging tbody tr",

  // ── Legacy aliases (kept for backward compatibility with browser-search.js) ──
  districtCodeInput: 'select[name="districtCode"]',
  sroCodeInput:      'select[name="sroCode"]',
  villageCodeInput:  'select[name="gaonCode1"]',
};
