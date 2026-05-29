import { createBrowserContext }
from "../modules/igrsup/browser/context.js";

import { browserPropertySearch }
from "../modules/igrsup/property/browser-search.js";

async function main() {

    // ======================
    // START BROWSER
    // ======================

    const {
        browser,
        page,
    } = await createBrowserContext();

    // ======================
    // OPEN WEBSITE
    // ======================

    await page.goto(
        "https://igrsup.gov.in/igrsup/userServicesHomeAction",
        {
            waitUntil: "networkidle"
        }
    );

    console.log("Website opened");

    // ======================
    // WAIT FOR MANUAL LOGIN
    // ======================

    console.log(
        "LOGIN MANUALLY THEN PRESS ENTER"
    );

    process.stdin.resume();

    process.stdin.once("data", async () => {

        // ======================
        // RUN PROPERTY SEARCH
        // ======================
const records =
    await browserPropertySearch(page, {

                districtCode: "177",

                sroCode: "122",

                villageCode: "166138",

                propertyId: "22",

                propertyAddress: "22",

            });

        console.log(
    JSON.stringify(records, null, 2)
);

        console.log(
            "RESULT SAVED"
        );

    });

}

main();