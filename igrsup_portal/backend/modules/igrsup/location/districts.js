import fs from "fs";

export async function getDistricts() {

  // LOAD SESSION
  const cookies = JSON.parse(
    fs.readFileSync(
      "./data/sessions/igrsup-session.json",
      "utf-8"
    )
  );

  // COOKIE HEADER
  const cookieHeader = cookies
    .map(
      cookie =>
        `${cookie.name}=${cookie.value}`
    )
    .join("; ");

  // REQUEST
  const response = await fetch(
    "https://igrsup.gov.in/igrsup/getDistrictNameEngJson",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/x-www-form-urlencoded",

        "Cookie":
          cookieHeader,

        "X-Requested-With":
          "XMLHttpRequest",
      },
    }
  );

  // JSON
  const data = await response.json();

  return data;
}