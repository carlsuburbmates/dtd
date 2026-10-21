/**
 * Retired unsafe live acceptance runner.
 *
 * The historical version embedded an administrator credential, injected it
 * into browser storage, and could create persistent business records without
 * deterministic cleanup. It must not be restored or executed.
 */

console.error(
  "This live acceptance runner has been retired. It makes no network requests. " +
    "Use the current approved sandbox acceptance procedures with synthetic fixtures and verified cleanup."
);
process.exitCode = 2;
