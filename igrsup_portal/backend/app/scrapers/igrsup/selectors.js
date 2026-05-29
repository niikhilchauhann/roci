export const IGRSUP_SELECTORS = {
  propertySearchForm: "form",

  // ── Dropdowns (the form uses <select>, NOT <input>) ──
  districtSelect:  'select[name="districtCode"]',
  sroSelect:       'select[name="sroCode"]',
  villageSelect:   'select[name="gaonCode1"]',

  // ── Text inputs ──
  propertyIdInput:      '#propertyId',
  propertyAddressInput: 'input[name="propNEWAddress"]',

  // ── Submit ──
  submitButton:
    'input[type="submit"], button[type="submit"], a[onclick*="submit"]',

  // ── Results ──
  resultTable: "table#tablepaging",
  resultRows:  "table#tablepaging tbody tr",

  // ── Legacy aliases (kept for backward compatibility with client.js) ──
  districtCodeInput: 'select[name="districtCode"]',
  sroCodeInput:      'select[name="sroCode"]',
  villageCodeInput:  'select[name="gaonCode1"]',
};