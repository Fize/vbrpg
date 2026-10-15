import { describe, expect, it } from "vitest";
import { downMigrationFileName, selectUpMigrationFiles } from "./migrations.js";

describe("migration files", () => {
  it("excludes rollback sidecars and orders the rest", () => {
    expect(
      selectUpMigrationFiles([
        "0005_phase1_auth_providers.down.sql",
        "0005_phase1_auth_providers.sql",
        "0001_platform_control_plane.sql",
      ]),
    ).toEqual(["0001_platform_control_plane.sql", "0005_phase1_auth_providers.sql"]);
  });

  it("ignores non-sql files", () => {
    expect(selectUpMigrationFiles(["README.md", "notes.txt"])).toEqual([]);
  });

  it("pairs a sidecar to its up migration", () => {
    expect(downMigrationFileName("0005_phase1_auth_providers.sql")).toBe(
      "0005_phase1_auth_providers.down.sql",
    );
  });
});
