export function selectUpMigrationFiles(fileNames: readonly string[]): string[] {
  return fileNames
    .filter((fileName) => fileName.endsWith(".sql"))
    // A `.down.sql` sidecar is a rollback body, never a forward migration.
    .filter((fileName) => !fileName.endsWith(".down.sql"))
    .sort();
}

export function downMigrationFileName(upFileName: string): string {
  return `${upFileName.slice(0, -4)}.down.sql`;
}
