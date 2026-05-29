export async function getVillagesBySRO(page, {

    districtCode,
    sroCode,

}) {

    console.log("LOADING VILLAGES");

    // =========================
    // OPEN PAGE
    // =========================

    await page.goto(
        "https://igrsup.gov.in/igrsup/us_newPropertySearchAction",
        {
            waitUntil: "networkidle"
        }
    );

    // =========================
    // SELECT DISTRICT
    // =========================

    await page.selectOption(
        "#districtCode",
        districtCode
    );

    // =========================
    // SELECT SRO
    // =========================

    await page.selectOption(
        "#sroCode",
        sroCode
    );

    // =========================
    // WAIT PAGE RELOAD
    // =========================

    await page.waitForTimeout(5000);

    // =========================
    // EXTRACT VILLAGES
    // =========================

    const villages = await page.evaluate(() => {

        const options = Array.from(
            document.querySelectorAll(
                "#villageCode3 option"
            )
        );

        return options.map(option => ({
            value: option.value,
            text: option.textContent.trim(),
        }));

    });

    console.log(
        `FOUND ${villages.length} VILLAGES`
    );

    return villages;
}