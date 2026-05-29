import { IGRSUP_SELECTORS } from "./selectors.js";

export async function openPropertySearchPage(page) {
  await page.goto(
    "https://igrsup.gov.in/igrsup/us_newPropertySearchAction",
    {
      waitUntil: "networkidle",
    }
  );

  await page.waitForSelector(
    IGRSUP_SELECTORS.propertySearchForm
  );
}

export async function fillPropertySearchForm(page, data) {
  await page.evaluate(
    ({ selectors, formData }) => {
      document.querySelector(
        selectors.districtCodeInput
      ).value = formData.districtCode;

      document.querySelector(
        selectors.sroCodeInput
      ).value = formData.sroCode;

      document.querySelector(
        selectors.villageCodeInput
      ).value = formData.villageCode;

      document.querySelector(
        selectors.propertyIdInput
      ).value = formData.propertyId;

      document.querySelector(
        selectors.propertyAddressInput
      ).value = formData.propertyAddress;
    },
    {
      selectors: IGRSUP_SELECTORS,
      formData: data,
    }
  );
}

export async function submitPropertySearchForm(page) {
  await page.evaluate(selector => {
    const form =
      document.querySelector(selector);

    form.submit();
  }, IGRSUP_SELECTORS.propertySearchForm);
}

export async function waitForPropertyResults(page) {
  await page.waitForSelector(
    IGRSUP_SELECTORS.resultTable,
    {
      timeout: 15000,
    }
  );
}

export async function fetchPropertyResultsHTML(page) {
  return page.content();
}

export async function runPropertySearch(page, data) {
  await openPropertySearchPage(page);
  await fillPropertySearchForm(page, data);
  await submitPropertySearchForm(page);
  await waitForPropertyResults(page);

  return fetchPropertyResultsHTML(page);
}
