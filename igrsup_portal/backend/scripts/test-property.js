import axios from "axios";
import fs from "fs";

async function main() {

  // LOAD SESSION COOKIES
  const cookies = JSON.parse(
    fs.readFileSync(
      "./data/sessions/igrsup-session.json",
      "utf-8"
    )
  );

  // BUILD COOKIE HEADER
  const cookieHeader = cookies
    .map(c => `${c.name}=${c.value}`)
    .join("; ");

  console.log("COOKIE HEADER:");
  console.log(cookieHeader);

  // CREATE REQUEST
  const response = await axios.post(
    "https://igrsup.gov.in/igrsup/us_newPropertySearchAction",

    new URLSearchParams({
      districtCode: "177",
      sroCode: "122",
      propertyId: "",
      propNEWAddress: "22",
      gaonCode1: "166138",
      "action:getPropertyDeedSearchDetail":
        "सम्पत्ति लेखपत्र विवरण(Property Deed)"
    }),

    {
      headers: {

        "Content-Type":
          "application/x-www-form-urlencoded",

        "Cookie":
          cookieHeader,

        "User-Agent":
          "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",

        "Origin":
          "https://igrsup.gov.in",

        "Referer":
          "https://igrsup.gov.in/igrsup/us_newPropertySearchAction"
      }
    }
  );

  console.log("STATUS:");
  console.log(response.status);

  console.log("HTML LENGTH:");
  console.log(response.data.length);

  // SAVE HTML
  fs.writeFileSync(
    "./data/raw/property-response.html",
    response.data
  );

  console.log(
    "HTML saved to property-response.html"
  );
}

main();