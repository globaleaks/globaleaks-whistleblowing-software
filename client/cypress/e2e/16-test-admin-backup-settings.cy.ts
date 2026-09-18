describe("admin backup settings", () => {
  it("should enable backup and persist time, period and retention", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="backup"]').click().should("be.visible");

    cy.get('#backup-time').clear().type('03:30');
    cy.get('#backup-period').select('6');
    cy.get('#backup-retention').clear().type('10');
    cy.get('#backup-enable').click();

    cy.visit("/#/admin/settings");
    cy.get('[data-cy="backup"]').click().should("be.visible");
    cy.get('#backup-disable').should("be.visible");
    cy.get('#backup-status').should("be.visible");
    cy.get('#backup-time').should('have.value', '03:30');
    cy.get('#backup-period').find('option:selected').should('have.text', '6');
    cy.get('#backup-retention').should('have.value', '10');
    // the backup is photographed configured and enabled, as the chapter shows it
    cy.takeScreenshot("admin/backup_settings");
    cy.logout();
  });

  it("should disable backup", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="backup"]').click().should("be.visible");
    cy.get('#backup-disable').click();

    cy.visit("/#/admin/settings");
    cy.get('[data-cy="backup"]').click().should("be.visible");
    cy.get('#backup-enable').should("be.visible");
    cy.logout();
  });
});
