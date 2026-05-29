import { getDistricts }
from "../modules/igrsup/location/districts.js";

async function main() {

  const districts =
    await getDistricts();

  console.log(
    JSON.stringify(districts, null, 2)
  );

}

main();