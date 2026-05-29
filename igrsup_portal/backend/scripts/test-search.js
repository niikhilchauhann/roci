import { searchProperty } from
  "../modules/igrsup/property/search.js";

async function main() {

  const records =
    await searchProperty({

      districtCode: "177",
      sroCode: "122",
      villageCode: "166138",
      propertyId: "22",
      propertyAddress: "22",

    });

  console.log(
    JSON.stringify(records, null, 2)
  );

}

main();