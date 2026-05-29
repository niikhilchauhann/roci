import fs from "fs";

import { parsePropertyHTML } from "./parser.js";

// ======================
// PROPERTY SEARCH
// ======================

export async function searchProperty({

  districtCode,
  sroCode,
  villageCode = "",   // empty string = tehsil-wide (no village filter)
  propertyId = "",
  propertyAddress = "",

}) {

  // ======================
  // LOAD SESSION
  // ======================

  const sessionFile =
    process.env.IGRSUP_SESSION_PATH ??
    "./data/sessions/igrsup-session.json";

  const sessionData = JSON.parse(
    fs.readFileSync(sessionFile, "utf-8")
  );
  const cookies = Array.isArray(sessionData) ? sessionData : sessionData.cookies;

  // ======================
  // COOKIE HEADER
  // ======================

  const cookieHeader = cookies
    .map(cookie =>
      `${cookie.name}=${cookie.value}`
    )
    .join("; ");

  console.log("COOKIE:");
  console.log(cookieHeader);

  // ======================
  // FORM DATA
  // ======================

  const formData = new URLSearchParams();

  formData.append(
    "districtCode",
    districtCode
  );

  formData.append(
    "sroCode",
    sroCode
  );

  formData.append(
    "propertyId",
    propertyId
  );

  formData.append(
    "propNEWAddress",
    propertyAddress
  );

  formData.append(
    "gaonCode1",
    villageCode
  );

  formData.append(
    "action:getPropertyDeedSearchDetail",
    "सम्पत्ति विलेख विवरण(Property Deed)"
  );

  console.log("FORM DATA:");
  console.log(formData.toString());

  // ======================
  // REQUEST
  // ======================

  const response = await fetch(
    "https://igrsup.gov.in/igrsup/us_newPropertySearchAction",
    {
      method: "POST",

      headers: {

        "Accept":
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",

        "Content-Type":
          "application/x-www-form-urlencoded",

        "Origin":
          "https://igrsup.gov.in",

        "Referer":
          "https://igrsup.gov.in/igrsup/us_newPropertySearchAction",

        "User-Agent":
          "Mozilla/5.0",

        "Cookie":
          cookieHeader,
      },

      body: formData.toString(),
    }
  );

  // ======================
  // RESPONSE INFO
  // ======================

  console.log("STATUS:");
  console.log(response.status);

  console.log("FINAL URL:");
  console.log(response.url);

  // ======================
  // HTML
  // ======================

  const html = await response.text();

  console.log("HTML LENGTH:");
  console.log(html.length);

  console.log("HTML PREVIEW:");
  console.log(
    html.slice(0, 1000)
  );

  // ======================
  // SAVE RAW HTML
  // ======================

  fs.writeFileSync(
    "./data/raw/property-response.html",
    html
  );

  console.log(
    "Raw HTML saved"
  );

  // ======================
  // PARSE
  // ======================

  const records =
    parsePropertyHTML(html);

  console.log(
    `Parsed ${records.length} records`
  );

  return records;
}