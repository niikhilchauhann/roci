/**
 * run-bulk-igrsup.js — Bulk property scraper for igrsup.gov.in
 *
 * Directly based on the working run-igrsup-parser.js single-property script.
 * The ONLY difference: loops over propertyId values from villages.json.
 *
 * Input:  ./data/input/villages.json
 * Output: ./data/exports/<district>/<sro>/<village>/<village>_<start>-<end>.csv
 *
 * villages.json format:
 * [{ "district":"Ayodhya", "sro":"Sadar", "village":"Akbar Bazar",
 *    "districtCode":"177", "sroCode":"120", "gaonCode":"000059",
 *    "startProperty":1, "endProperty":100 }]
 */

import fs from "fs";
import { launchBrowser }     from "../modules/igrsup/browser/browser.js";
import { parsePropertyHTML } from "../modules/igrsup/property/parser.js";

// ─── CSV ───────────────────────────────────────────────────────────────────

const CSV_COLUMNS = [
  "district","sro","village","searched_property_id","document_id",
  "serial_no","registration_year","registration_no","party_name",
  "address","property_details","khasra","registration_date","deed_type","action",
];

const escapeCSV = v => `"${String(v??'').replace(/"/g,'""')}"`;

function ensureCSV(p) {
  fs.mkdirSync(p.slice(0, p.lastIndexOf("/")), { recursive:true });
  if (!fs.existsSync(p))
    fs.writeFileSync(p, `\uFEFF${CSV_COLUMNS.join(",")}\n`, "utf-8");
}

function appendCSV(p, rows) {
  if (!rows.length) return;
  fs.appendFileSync(p,
    rows.map(r => CSV_COLUMNS.map(c => escapeCSV(r[c])).join(",")).join("\n") + "\n",
    "utf-8");
}

// ─── Progress ──────────────────────────────────────────────────────────────

const progressPath = csv => csv.replace(/\.csv$/, ".progress.json");

function loadProgress(csv) {
  const p = progressPath(csv);
  return fs.existsSync(p)
    ? JSON.parse(fs.readFileSync(p, "utf-8"))
    : { completedIds:[], seenDocuments:[] };
}

function saveProgress(csv, done, seen) {
  fs.writeFileSync(progressPath(csv),
    JSON.stringify({ completedIds:[...done], seenDocuments:[...seen] }, null, 2),
    "utf-8");
}

// ─── Utils ─────────────────────────────────────────────────────────────────

const slugify = v =>
  String(v||"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"");
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ─── Helpers copied EXACTLY from working single-property script ────────────

const SEARCH_URL = "https://igrsup.gov.in/igrsup/us_newPropertySearchAction";

/**
 * Waits until an AJAX-populated <select> has a specific option value.
 * Copied exactly from run-igrsup-parser.js.
 */
async function waitForOptionValue(locator, value) {
  await locator.waitFor({ state:"visible", timeout:0 });
  await locator.page().waitForFunction(
    ({ selector, optionValue }) => {
      const element = document.querySelector(selector);
      if (!element) return false;
      return Array.from(element.options||[]).some(o => o.value === optionValue);
    },
    {
      selector: await locator.evaluate(element => {
        if (element.id)   return `#${element.id}`;
        if (element.name) return `${element.tagName.toLowerCase()}[name="${element.name}"]`;
        return "";
      }),
      optionValue: value,
    },
    { timeout:0 }
  );
}

/**
 * Pause and wait for the user to log in manually in the browser.
 * Copied exactly from run-igrsup-parser.js.
 */
async function pauseForManualLogin(label = "LOGIN MANUALLY IN BROWSER") {
  console.log("");
  console.log("=================================");
  console.log(label);
  console.log("AFTER LOGIN PRESS ENTER");
  console.log("=================================");
  console.log("");
  process.stdin.resume();
  await new Promise(resolve => process.stdin.once("data", () => resolve()));
}

/**
 * Scrape one property ID.
 *
 * This is run-igrsup-parser.js main() converted into a reusable function.
 * The only changes:
 *   - accepts districtCode/sroCode/gaonCode/propertyId as parameters
 *   - returns parsed rows instead of writing files
 *   - does NOT ask for login (caller handles that once at startup)
 */
async function scrapeProperty(page, context, {
  districtCode, sroCode, gaonCode, propertyId,
}) {
  // Navigate to search page fresh for each property
  await page.goto(SEARCH_URL, { waitUntil:"networkidle", timeout:0 });

  console.log(`  [PAGE] Property search page loaded`);

  // ── Locators — same as working single script ──
  const districtSelect = page.locator('select[name="districtCode"]');
  const sroLocator     = page.locator('select[name="sroCode"]');
  const villageLocator = page.locator('select[name="gaonCode1"]');
  const submitLocator  = page.locator('input[type="submit"], button[type="submit"]').first();

  // ── District ──
  await districtSelect.waitFor({ state:"attached", timeout:60000 });
  await page.waitForTimeout(5000); // let page JS initialise — same as working script
  await districtSelect.selectOption({ value: districtCode });
  await page.waitForTimeout(3000);
  console.log(`  [FORM] District selected`);

  // ── SRO ──
  await waitForOptionValue(sroLocator, sroCode);
  await sroLocator.selectOption({ value: sroCode });
  await page.waitForTimeout(3000);
  console.log(`  [FORM] SRO selected`);

  // ── Village ──
  await waitForOptionValue(villageLocator, gaonCode);
  await villageLocator.selectOption({ value: gaonCode });
  await page.waitForTimeout(3000);
  console.log(`  [FORM] Village selected`);

  // ── Wait for Khasra field to activate ──
  // Copied exactly from working single script
  await page.waitForFunction(() => {
    const el = document.querySelector("#propertyId");
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden" && !el.disabled;
  }, { timeout:60000 });

  await page.waitForTimeout(2000);
  console.log(`  [FORM] Khasra field activated`);

  // ── Fill Khasra/Property ID ──
  // Copied exactly from working single script (scoring + marker approach)
  const selectedField = await page.evaluate(() => {
    const isVisible = el =>
      !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);

    const getContextText = el =>
      (el.closest("tr,td,div,li,p")?.innerText || "").toLowerCase();

    const candidates = [...document.querySelectorAll("input[type='text'],textarea")]
      .filter(el => isVisible(el) && !el.disabled && !el.readOnly)
      .map((el, index) => {
        const contextText = getContextText(el);
        const idText      = `${el.id} ${el.name}`.toLowerCase();
        let score = 0;
        if (/खसरा|गाटा|plot|khasra|property/i.test(contextText)) score += 50;
        if (/propertyid|propertynum|khasra|plot/i.test(idText))   score += 40;
        if (/address|पता|propnewaddress/i.test(contextText + " " + idText)) score -= 100;
        return { index, score, id:el.id, name:el.name, outerHTML:el.outerHTML };
      })
      .sort((a,b) => b.score - a.score);

    const selected = candidates[0];
    if (!selected) throw new Error("No visible editable property candidate found");

    const target = [...document.querySelectorAll("input[type='text'],textarea")]
      .filter(el => isVisible(el) && !el.disabled && !el.readOnly)[selected.index];

    if (!target) throw new Error("Selected property element no longer available");

    target.setAttribute("data-igrsup-property-target", "true");
    return selected;
  });

  console.log(`  [FORM] Khasra field: id="${selectedField.id}" name="${selectedField.name}"`);

  // Fill the tagged element
  await page.evaluate(value => {
    const input = document.querySelector('[data-igrsup-property-target="true"]');
    if (!input) throw new Error("Active property field not found");
    input.removeAttribute("readonly");
    input.disabled = false;
    input.focus();
    input.value = value;
    input.dispatchEvent(new Event("input",  { bubbles:true }));
    input.dispatchEvent(new Event("change", { bubbles:true }));
    input.dispatchEvent(new KeyboardEvent("keyup", { bubbles:true }));
    input.blur();
  }, String(propertyId));

  await page.waitForTimeout(2000);

  // Verify
  const finalValue = await page.evaluate(
    () => document.querySelector('[data-igrsup-property-target="true"]')?.value ?? null
  );
  if (!finalValue?.trim()) throw new Error("Property value still empty after DOM injection");
  console.log(`  [FORM] Khasra confirmed: "${finalValue}"`);

  // ── Submit ──
  await submitLocator.waitFor({ state:"visible", timeout:0 });
  await submitLocator.scrollIntoViewIfNeeded();
  await submitLocator.click({ force:true });
  console.log(`  [FORM] Submitted`);
  await page.waitForTimeout(5000);

  // ── Click Property Deed accordion → opens popup ──
  // Copied exactly from working single script
  const deedButton = page.locator('input[name="action:getPropertyDeedSearchDetail"]');
  const deedCount  = await deedButton.count();

  if (deedCount === 0) {
    console.log(`  [RESULT] No deed button — property ${propertyId} has no results`);
    return [];
  }

  const popupPromise = page.waitForEvent("popup");
  await deedButton.click();
  const reportPage = await popupPromise;

  await reportPage.waitForLoadState("domcontentloaded");
  await reportPage.waitForTimeout(5000);

  console.log(`  [POPUP] ${reportPage.url()}`);

  const reportHtml = await reportPage.content();
  await reportPage.close();

  return parsePropertyHTML(reportHtml);
}

// ─── Main ──────────────────────────────────────────────────────────────────

async function main() {
  const inputPath = "./data/input/villages.json";
  if (!fs.existsSync(inputPath)) {
    console.error(`[ERROR] Not found: ${inputPath}`); process.exit(1);
  }

  const villages = JSON.parse(fs.readFileSync(inputPath, "utf-8"));
  console.log(`[BULK] ${villages.length} village(s) loaded`);

  const { browser, context, page } = await launchBrowser();

  try {
    // ── One-time login at startup — exactly like single script ──
    console.log("[SESSION] Loaded");

    await page.goto(SEARCH_URL, { waitUntil:"networkidle", timeout:0 });

    await pauseForManualLogin();

    fs.mkdirSync("./data/sessions", { recursive:true });
    await context.storageState({ path:"./data/sessions/igrsup-session.json" });
    console.log("[SESSION] Session saved");

    // ── Loop over villages ──
    for (const v of villages) {
      const { district, sro, village,
              districtCode, sroCode, gaonCode,
              startProperty, endProperty } = v;

      console.log(`\n${"=".repeat(55)}`);
      console.log(`[VILLAGE] ${village}  (${district} / ${sro})`);
      console.log(`[RANGE]   ${startProperty} → ${endProperty}`);
      console.log("=".repeat(55));

      const dir     = `./data/exports/${slugify(district)}/${slugify(sro)}/${slugify(village)}`;
      const csvPath = `${dir}/${slugify(village)}_${startProperty}-${endProperty}.csv`;

      ensureCSV(csvPath);

      const prog = loadProgress(csvPath);
      const done = new Set(prog.completedIds.map(Number));
      const seen = new Set(prog.seenDocuments);

      if (done.size > 0) console.log(`[RESUME] Skipping ${done.size} already done`);

      let saved = 0, empty = 0, errors = 0;

      for (let pid = startProperty; pid <= endProperty; pid++) {
        if (done.has(pid)) continue;

        process.stdout.write(`  [${String(pid).padStart(4)}/${endProperty}] `);

        try {
          const rows = await scrapeProperty(page, context, {
            districtCode, sroCode, gaonCode, propertyId: pid,
          });

          if (!rows.length) {
            process.stdout.write("empty\n");
            empty++;
          } else {
            const enriched = rows
              .map(row => ({
                district, sro, village,
                searched_property_id: String(pid),
                document_id: `${row.registration_year}_${row.registration_no}`,
                ...row,
              }))
              .filter(row => {
                if (seen.has(row.document_id)) return false;
                seen.add(row.document_id);
                return true;
              });

            if (enriched.length) {
              appendCSV(csvPath, enriched);
              process.stdout.write(`saved ${enriched.length}\n`);
              saved += enriched.length;
            } else {
              process.stdout.write("duplicate — skipped\n");
              empty++;
            }
          }

          done.add(pid);
          saveProgress(csvPath, done, seen);

        } catch (err) {
          process.stdout.write(`ERROR: ${err.message}\n`);
          errors++;

          // If session expired, pause for re-login then continue
          if (err.message?.toLowerCase().includes("login") ||
              err.message?.toLowerCase().includes("session") ||
              page.url().includes("Login") || page.url().includes("login")) {
            console.log("\n[AUTH] Session expired — please log in again");
            await page.goto(SEARCH_URL, { waitUntil:"networkidle", timeout:0 });
            await pauseForManualLogin("SESSION EXPIRED — LOGIN AGAIN");
            fs.mkdirSync("./data/sessions", { recursive:true });
            await context.storageState({ path:"./data/sessions/igrsup-session.json" });
            console.log("[AUTH] Session saved, resuming...");
          }

          await sleep(3000);
        }

        await sleep(2000);
      }

      console.log(`\n[DONE] ${village}`);
      console.log(`  Saved:  ${saved} rows`);
      console.log(`  Empty:  ${empty}`);
      console.log(`  Errors: ${errors}`);
      console.log(`  File:   ${csvPath}`);
    }

    console.log("\n[BULK] All villages complete ✓");

  } catch (err) {
    console.error(err);
    console.log("\n=================================");
    console.log("SCRIPT FAILED");
    console.log("BROWSER KEPT OPEN FOR DEBUGGING");
    console.log("=================================");
    await new Promise(() => {}); // keep browser open
  } finally {
    // browser.close() intentionally omitted from catch path above
  }
}

main();
