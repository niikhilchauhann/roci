import fs from "fs";
import { exportTransactions, createExportBaseName }
from "./exporter.js";
import { parsePropertyHTML } from "./parser.js";
import { PROPERTY_SELECTORS } from "./selectors.js";

export async function browserPropertySearch(page, {

    districtCode,
    sroCode,
    villageCode,
    villageName = "",
    propertyId,
    propertyAddress,
    exportDir = "./data/exports",

}) {

    console.log("START PROPERTY SEARCH");

    // =========================
    // OPEN SEARCH PAGE
    // =========================

    await page.goto(
        PROPERTY_SELECTORS.searchPage,
        {
            waitUntil: "networkidle"
        }
    );

    await page.waitForSelector(
        PROPERTY_SELECTORS.form
    );

    // =========================
    // FILL FORM
    // =========================

    await page.evaluate((data) => {
        function dispatchChange(element) {
            element.dispatchEvent(
                new Event("change", {
                    bubbles: true
                })
            );
        }

        function setInputValue(selector, value) {
            const input =
                document.querySelector(selector);

            if (!input) {
                throw new Error(
                    `Missing input: ${selector}`
                );
            }

            input.value = value ?? "";
            dispatchChange(input);
        }

        setInputValue(
            data.selectors.districtCodeInput,
            data.districtCode
        );

        setInputValue(
            data.selectors.sroCodeInput,
            data.sroCode
        );

        setInputValue(
            data.selectors.villageCodeInput,
            data.villageCode
        );

        setInputValue(
            data.selectors.propertyIdInput,
            data.propertyId
        );

        setInputValue(
            data.selectors.propertyAddressInput,
            data.propertyAddress
        );

    }, {
        selectors: PROPERTY_SELECTORS,
        districtCode,
        sroCode,
        villageCode,
        propertyId,
        propertyAddress,
    });

    // =========================
    // SUBMIT FORM
    // =========================

    await page.evaluate((selector) => {

    const form =
        document.querySelector(
            selector
        );

    form.submit();

}, PROPERTY_SELECTORS.form);

    await page.waitForSelector(
        PROPERTY_SELECTORS.resultTable,
        {
            timeout: 15000
        }
    );

    console.log("SEARCH COMPLETE");

    // =========================
    // GET HTML
    // =========================

    const html = await page.content();

    // SAVE RAW HTML
    fs.writeFileSync(
        "./data/raw/property-search-result.html",
        html,
        "utf-8"
    );

    const records =
        parsePropertyHTML(html);

    const exportBaseName =
        createExportBaseName({
            villageName,
            villageCode,
            propertyId,
            propertyAddress,
        });

    const exportPaths =
        exportTransactions(
            `${exportDir}/${exportBaseName}`,
            records
        );

    console.log(
        `Parsed ${records.length} records`
    );

    console.log("JSON EXPORT:");
    console.log(exportPaths.jsonPath);

    console.log("CSV EXPORT:");
    console.log(exportPaths.csvPath);

    return records;
}
