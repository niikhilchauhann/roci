import fs from "fs";

import { launchBrowser }
from "../modules/igrsup/browser/browser.js";

async function main() {

  console.log(
    "Launching browser..."
  );

  const {
    browser,
    context,
    page
  } = await launchBrowser();

  // =========================
  // LOAD SESSION FILE
  // =========================

  console.log(
    "Loading saved session..."
  );

  const cookies = JSON.parse(
    fs.readFileSync(
      "./data/sessions/igrsup-session.json",
      "utf-8"
    )
  );

  console.log(
    "Cookies loaded:"
  );

  console.log(cookies);

  // =========================
  // INJECT COOKIES
  // =========================

  await context.addCookies(cookies);

  console.log(
    "Cookies injected into browser"
  );

  // =========================
  // OPEN DASHBOARD DIRECTLY
  // =========================

  console.log(
    "Opening dashboard..."
  );

  await page.goto(
    "https://igrsup.gov.in/igrsup/userServicesDashboardAction",
    {
      waitUntil: "networkidle"
    }
  );

  console.log(
    "Dashboard page loaded"
  );

  // =========================
  // VERIFY LOGIN
  // =========================

  const currentURL = page.url();

  console.log(
    "CURRENT URL:",
    currentURL
  );

  if (
    currentURL.includes(
      "userServicesDashboardAction"
    )
  ) {

    console.log(`
==================================
SESSION REUSE SUCCESSFUL
User already authenticated
==================================
`);

  } else {

    console.log(`
==================================
SESSION EXPIRED
Need fresh login
==================================
`);

  }

  // Keep browser open
  await page.pause();

}

main();