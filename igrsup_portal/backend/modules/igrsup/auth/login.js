import axios from "axios";
import { sha512 } from "js-sha512";

const BASE_URL = "https://igrsup.gov.in";

export async function loginIGRSUP({
  username,
  password,
  captcha,
  otp = null,
}) {
  try {
    console.log("STEP 1 — Create session");

    const session = axios.create({
      baseURL: BASE_URL,
      withCredentials: true,
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",

        "Accept": "*/*",

        "Accept-Language":
          "en-GB,en-US;q=0.9,en;q=0.8",

        "Origin":
          "https://igrsup.gov.in",

        "Referer":
          "https://igrsup.gov.in/igrsup/userServicesHomeAction",

        "X-Requested-With":
          "XMLHttpRequest",

        "Content-Type":
          "application/x-www-form-urlencoded",
      },
    });

    // =========================
    // LOAD LOGIN PAGE
    // =========================

    console.log("STEP 2 — Load login page");

    const loginPage = await session.get(
      "/igrsup/userServicesHomeAction"
    );

    console.log(
      "COOKIES:",
      loginPage.headers["set-cookie"]
    );

    const html = loginPage.data;

    // =========================
    // EXTRACT SALT
    // =========================

    const saltMatch = html.match(
      /salt\s*=\s*['"](.*?)['"]/
    );

    let salt = "";

    if (saltMatch && saltMatch[1]) {
      salt = saltMatch[1];
    }

    console.log("SALT:", salt);

    // =========================
    // HASH PASSWORD
    // =========================

    const firstHash = sha512(password);

    const hashedPassword =
      sha512(firstHash + salt);

    console.log("Password hashed");

    // =========================
    // LOGIN REQUEST
    // =========================

    const loginPayload =
      `user_appId=${encodeURIComponent(username)}` +
      `&user_pass=${encodeURIComponent(hashedPassword)}`;

    console.log("STEP 3 — Send login request");

    const loginResponse = await session.post(
      "/igrsup/us_multifactorAuth.action",
      loginPayload
    );

    console.log("LOGIN RESPONSE:");
    console.log(loginResponse.data);

    // =========================
    // OTP REQUIRED
    // =========================

    if (!otp) {
      return {
        success: true,
        otpRequired: true,
        message: "OTP may have been sent",
        data: loginResponse.data,
        session,
      };
    }

    // =========================
    // VERIFY OTP
    // =========================

    console.log("STEP 4 — Verify OTP");

    const otpPayload =
      `enter_otp=${encodeURIComponent(otp)}`;

    const otpResponse = await session.post(
      "/igrsup/us_verify_user_otp.action",
      otpPayload
    );

    console.log("OTP RESPONSE:");
    console.log(otpResponse.data);

    return {
      success: true,
      loggedIn: true,
      data: otpResponse.data,
      cookies:
        otpResponse.headers["set-cookie"] || [],
    };

  } catch (error) {

    console.error("LOGIN ERROR");

    if (error.response) {
      console.error(error.response.data);
    }

    console.error(error.message);

    return {
      success: false,
      error: error.message,
    };
  }
}