// The label of the interface in the language of the run: the English one when
// the catalogue has no entry for it
export const t = (key: string): string => {
  const l10n = Cypress.env("l10n") || {};
  return l10n[key] || key;
};
