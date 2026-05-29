/**
 * generate-villages.js
 *
 * Automatically discovers all SROs and villages in Ayodhya district
 * from the IGRSUP property search page and writes villages.json.
 *
 * Usage:   node scripts/generate-villages.js
 * Output:  ./data/input/villages.json
 * Then:    node scripts/run-bulk-igrsup.js
 */

import fs from "fs";
import { launchBrowser } from "../modules/igrsup/browser/browser.js";

// ─── Config ────────────────────────────────────────────────────────────────

const DISTRICT_NAME = "Ayodhya";
const DISTRICT_CODE = "177";
const SEARCH_URL = "https://igrsup.gov.in/igrsup/us_newPropertySearchAction";
const OUTPUT_PATH = "./data/input/villages.json";
const START_PROPERTY = 1;
const END_PROPERTY = 200;

// ─── Helpers ───────────────────────────────────────────────────────────────

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function pauseForManualLogin() {
  console.log("");
  console.log("=================================");
  console.log("LOGIN MANUALLY IN BROWSER");
  console.log("AFTER LOGIN PRESS ENTER");
  console.log("=================================");
  console.log("");
  process.stdin.resume();
  await new Promise(resolve => process.stdin.once("data", () => resolve()));
}

async function extractOptions(page, selector) {
  return page.evaluate(sel => {
    const el = document.querySelector(sel);
    if (!el) return [];
    return Array.from(el.options)
      .filter(o =>
        o.value &&
        o.value !== "0" &&
        o.value.trim() !== "" &&
        !/please\s*select|select\s*one|^\s*-/i.test(o.textContent)
      )
      .map(o => ({ value: o.value.trim(), text: o.textContent.trim() }));
  }, selector);
}

async function waitForSelectOptions(page, selector, timeout = 30000) {
  await page.waitForFunction(
    sel => {
      const el = document.querySelector(sel);
      if (!el) return false;
      return Array.from(el.options).some(
        o => o.value && o.value !== "0" && o.value.trim() !== ""
      );
    },
    selector,
    { timeout }
  );
}

/**
 * Navigate to the search form, handling all redirect scenarios:
 *
 *  A) Already on search form  → ✅ return
 *  B) Redirected to Dashboard → click Property Search link in sidebar
 *  C) Redirected to Login     → ask for manual login, save session, retry
 */
async function gotoSearchForm(page, context) {
  for (let attempt = 1; attempt <= 3; attempt++) {
    await page.goto(SEARCH_URL, { waitUntil: "networkidle", timeout: 0 });
    await sleep(2000);

    const url = page.url();
    console.log(`  [NAV] Landed: ${url.split("/igrsup/").pop()}`);

    // Case C — login page
    if (
      url.includes("Login") ||
      url.includes("login") ||
      url.includes("Home")
    ) {
      console.log("[AUTH] Login required");
      await pauseForManualLogin();
      fs.mkdirSync("./data/sessions", { recursive: true });
      await context.storageState({
        path: "./data/sessions/igrsup-session.json",
      });
      console.log("[AUTH] Session saved");
      continue; // retry after login
    }

    // Case B — dashboard redirect (session valid but search URL redirects)
    if (url.includes("Dashboard") || url.includes("dashboard")) {
      console.log("[NAV] On dashboard — clicking Property Search link...");
      try {
        // Try the sidebar "सम्पति खोजें" link
        await page.click(
          'a[href*="us_newPropertySearch"], a:has-text("सम्पति खोजें")',
          { timeout: 5000 }
        );
        await page.waitForLoadState("networkidle", { timeout: 0 });
        await sleep(2000);
      } catch {
        // Sidebar click failed — try direct URL one more time
        await page.goto(SEARCH_URL, { waitUntil: "networkidle", timeout: 0 });
        await sleep(2000);
      }
    }

    // Confirm #districtCode is in DOM (it's hidden on load, check "attached")
    const found = await page.locator("#districtCode").count();
    if (found > 0) {
      console.log("[NAV] Search form ready ✓");
      return; // ✅
    }

    console.log(`  [NAV] Form not ready, retry ${attempt}/3...`);
    await sleep(3000);
  }

  throw new Error("Cannot reach search form — please re-login and try again.");
}

// ─── Main ──────────────────────────────────────────────────────────────────

async function main() {
  const { browser, context, page } = await launchBrowser();

  try {

    // ── Step 1+2: Navigate to search form (handles login + dashboard) ─────
    console.log("[INIT] Opening IGRSUP property search page...");
    await gotoSearchForm(page, context);

    // ── Step 3: Select Ayodhya district ───────────────────────────────────
    console.log(`[DISTRICT] Selecting ${DISTRICT_NAME} (${DISTRICT_CODE})...`);

    await page.waitForSelector("#districtCode", {
      state: "attached",
      timeout: 30000,
    });

    await sleep(3000); // let page JS initialise
    await page.selectOption("#districtCode", DISTRICT_CODE);

    // ── Step 4: Wait for SRO AJAX, extract all SROs ───────────────────────
    console.log("[SRO] Waiting for SRO options...");
    await sleep(3000);
    await waitForSelectOptions(page, 'select[name="sroCode"]');

    const sros = await extractOptions(page, 'select[name="sroCode"]');

    if (!sros.length) {
      throw new Error("No SRO options found after selecting district");
    }

    console.log(`[SRO] Found ${sros.length} SROs:`);
    sros.forEach(s => console.log(`  ${s.value}  ${s.text}`));

    // ── Step 5: For each SRO extract all villages ─────────────────────────
    const entries = [];

    for (let si = 0; si < sros.length; si++) {
      const sro = sros[si];

      console.log(`\n[SRO ${si + 1}/${sros.length}] ${sro.text} (${sro.value})`);

      // Select SRO
      await page.selectOption('select[name="sroCode"]', sro.value);
      await sleep(3000); // wait for village AJAX

      // Wait for village dropdown to populate
      try {
        await waitForSelectOptions(page, "#villageCode3", 15000);
      } catch {
        console.log(`  [WARN] No villages loaded for SRO "${sro.text}" — skipping`);
        // Reset for next SRO
        await page.selectOption("#districtCode", DISTRICT_CODE);
        await sleep(3000);
        await waitForSelectOptions(page, 'select[name="sroCode"]').catch(() => { });
        continue;
      }

      const villages = await extractOptions(page, "#villageCode3");

      if (!villages.length) {
        console.log(`  [WARN] 0 villages for "${sro.text}" — skipping`);
        continue;
      }

      console.log(`  [VILLAGES] Found ${villages.length}`);
      villages.forEach(v => console.log(`    ${v.value}  ${v.text}`));

      for (const village of villages) {
        entries.push({
          district: DISTRICT_NAME,
          districtCode: DISTRICT_CODE,
          sro: sro.text,
          sroCode: sro.value,
          village: village.text,
          gaonCode: village.value,
          startProperty: START_PROPERTY,
          endProperty: END_PROPERTY,
        });
      }

      // Re-select district to reset SRO dropdown cleanly for next iteration
      await page.selectOption("#districtCode", DISTRICT_CODE);
      await sleep(3000);
      await waitForSelectOptions(page, 'select[name="sroCode"]').catch(() => { });
    }

    // ── Step 6: Save ──────────────────────────────────────────────────────
    if (!entries.length) {
      throw new Error("No villages found — discovery failed");
    }

    fs.mkdirSync("./data/input", { recursive: true });
    fs.writeFileSync(OUTPUT_PATH, JSON.stringify(entries, null, 2), "utf-8");

    const sroCount = new Set(entries.map(e => e.sroCode)).size;

    console.log("\n" + "=".repeat(50));
    console.log("[DONE] villages.json generated");
    console.log(`  District : ${DISTRICT_NAME} (${DISTRICT_CODE})`);
    console.log(`  SROs     : ${sroCount}`);
    console.log(`  Villages : ${entries.length}`);
    console.log(`  File     : ${OUTPUT_PATH}`);
    console.log("=".repeat(50));
    console.log("\nNext step:");
    console.log("  node scripts/run-bulk-igrsup.js");

  } finally {
    await browser.close();
  }
}

main().catch(err => {
  console.error("[FATAL]", err);
  process.exit(1);
});