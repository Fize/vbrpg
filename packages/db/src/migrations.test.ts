import assert from "node:assert/strict";
import test from "node:test";
import { downMigrationFileName, selectUpMigrationFiles } from "./migrations.js";

test("selectUpMigrationFiles excludes rollback sidecars", () => {
  assert.deepEqual(
    selectUpMigrationFiles([
      "0005_phase1_auth_providers.down.sql",
      "0005_phase1_auth_providers.sql",
      "0001_platform_control_plane.sql",
    ]),
    ["0001_platform_control_plane.sql", "0005_phase1_auth_providers.sql"],
  );
});

test("selectUpMigrationFiles ignores non-sql files", () => {
  assert.deepEqual(selectUpMigrationFiles(["README.md", "notes.txt"]), []);
});

test("downMigrationFileName pairs a sidecar to its up migration", () => {
  assert.equal(
    downMigrationFileName("0005_phase1_auth_providers.sql"),
    "0005_phase1_auth_providers.down.sql",
  );
});
