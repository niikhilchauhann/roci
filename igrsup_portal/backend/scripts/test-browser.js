import fs from "fs";

import { launchBrowser }
from "../modules/igrsup/browser/browser.js";

async function main() {

  const { browser, context, page }
    = await launchBrowser();

  // Open login page
  await page.goto(
    "https://igrsup.gov.in/igrsup/userServicesHomeAction"
  );

  console.log("Page loaded");

  // Fill username
  await page.fill(
    "#application_id",
    "D8055"
  );

  // Fill password
  await page.fill(
    "#login_password",
    "Dhruv@8055"
  );

  console.log(
    "Credentials filled"
  );

  console.log(`
==================================
MANUAL STEPS:
1. Enter captcha
2. Click Login
3. Enter OTP
4. Wait for dashboard
==================================
`);

  // WAIT UNTIL DASHBOARD LOADS
  await page.waitForURL(
    "**/userServicesDashboardAction",
    {
      timeout: 300000
    }
  );

  console.log(
    "Dashboard detected"
  );

  // =========================
  // SAVE COOKIES
  // =========================

  const cookies =
    await context.cookies();

  fs.writeFileSync(
    "./data/sessions/igrsup-session.json",
    JSON.stringify(
      cookies,
      null,
      2
    )
  );

  console.log(
    "Session saved successfully"
  );

  // Keep browser open
  await page.pause();

}

main();