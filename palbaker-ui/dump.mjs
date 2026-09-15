import fs from "fs";

const out = fs.createWriteStream("spawners.json", { flags: "w" });

// Start JSON array
out.write("[\n");

let first = true;

function writeSpawner(x, y) {
    const obj = {
        Type: "Sheet",
        Location: { X: x, Y: y, Z: 0 },
        Rotation: { Pitch: 0.0, Yaw: 0.0, Roll: 0.0 },
        SpawnerName: `PalSchema_Custom_Spawn_${x}_${y}`,
        SpawnGroupList: [
            {
                Weight: 50,
                PalList: [
                    {
                        PalId: "DomeArmorDragon",
                        Level: 1,
                        Level_Max: 1,
                        Num: 1,
                        Num_Max: 1
                    }
                ]
            }
        ]
    };

    if (!first) out.write(",\n");
    first = false;

    out.write(JSON.stringify(obj));
}

(async () => {
    for (let x = -5_000_00; x <= 5_000_00; x += 50000) {
        for (let y = -5_000_00; y <= 5_000_00; y += 50000) {
            writeSpawner(x, y);
        }
        // allow event loop to breathe
        await new Promise(r => setImmediate(r));
    }

    // End JSON array
    out.write("\n]\n");
    out.end();

    console.log("Finished writing spawners.json");
})();
