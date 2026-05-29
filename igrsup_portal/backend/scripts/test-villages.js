import { chromium } from "playwright";

import { getVillagesBySRO }
from "../modules/igrsup/location/villages.js";

async function main() {

    const browser =
        await chromium.launch({
            headless: false
        });

    const page =
        await browser.newPage();

    // OPEN WEBSITE FIRST
    await page.goto(
        "https://igrsup.gov.in/igrsup/userServicesHomeAction"
    );

    console.log(
        "LOGIN MANUALLY THEN PRESS ENTER"
    );

    process.stdin.once("data", async () => {

        const villages =
            await getVillagesBySRO(page, {

                districtCode: "177",

                sroCode: "120",

            });

        console.log(
            JSON.stringify(villages, null, 2)
        );

    });

}

main();