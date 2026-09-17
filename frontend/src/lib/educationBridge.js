// The First Leash is deployed as a separate application (see DTD-Education-extended).
// This module is the single source of truth for the bridge between the two products.
// Main directory -> First Leash: outbound links and legacy route redirects.
// First Leash -> Main directory: the owner intake dossier hands off to the directory root.
export const FIRST_LEASH_URL = (
    process.env.REACT_APP_FIRST_LEASH_URL || "https://learn.dogtrainersdirectory.com.au"
).replace(/\/+$/, "");

export const DIRECTORY_URL = (
    process.env.REACT_APP_DIRECTORY_URL || "https://dogtrainersdirectory.com.au"
).replace(/\/+$/, "");
