import { chromium } from "playwright";

export async function createBrowserContext() {

    console.log("Launching browser...");

    const browser = await chromium.launch({

        headless: false,

    });

    const context = await browser.newContext({

        viewport: {
            width: 1400,
            height: 900,
        }

    });

    const page = await context.newPage();

    return {
        browser,
        context,
        page,
    };
}