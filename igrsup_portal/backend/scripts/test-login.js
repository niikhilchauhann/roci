import { loginIGRSUP } from "../modules/igrsup/auth/login.js";

async function main() {

  // =========================
  // STEP 1 LOGIN
  // =========================

  const loginResult = await loginIGRSUP({
    username: "D8055",
    password: "Dhruv@8055",
    captcha: "1234"
  });

  console.log("LOGIN RESULT:");
  console.log(loginResult);

  // =========================
  // ENTER OTP HERE
  // =========================

  const otp = "123456";

  // =========================
  // STEP 2 VERIFY OTP
  // =========================

  const finalResult = await loginIGRSUP({
    username: "D8055",
    password: "Dhruv@8055",
    captcha: "1234",
    otp
  });

  console.log("FINAL RESULT:");
  console.log(finalResult);
}

main();