describe("admin configure, add, configure and delete tenants", () => {
  const add_profile = (name: string, tenant?: boolean) => {
    if (tenant) {
      cy.get(".show-add-tenant-btn").click();
      cy.get("[name='newTenant.name']").type(name);
      cy.get('select[name="profile"]').should('be.visible');
      cy.get('select[name="profile"]').select(1);
      cy.get("#add-btn").click();
      cy.contains(name).should("exist");
    } else {
      cy.get(".show-add-profile-btn").click();
      cy.get("[name='newTenant.name']").type(name);
      cy.get("#add-btn").click();
      cy.contains(name).should("exist");
    }
  };

  const add_tenant = async (name:string) => {
    cy.get(".show-add-tenant-btn").click();
    cy.get("[name='newTenant.name']").type(name);
    cy.get("#add-btn").click();
    cy.contains(name).should("exist");
  };

  it("should add, configure and delete tenant", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");

    add_tenant("Platform A");
    add_tenant("Platform B");
    add_tenant("Platform C");

    cy.takeScreenshot("admin/sites_management_sites");

    cy.get("button[name='configure_tenant']").last().click();
    cy.get("button[name='delete_tenant']").last().click();
    cy.get("#modal-action-ok").click();

    cy.get('[data-cy="options"]').click();
    cy.takeScreenshot("admin/sites_management_options");
    cy.logout();
  });
  it("should add and configure the profile tenant", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="profiles"]').click().should("be.visible").click();
    add_profile("Platform D");

    cy.intercept('GET', '/api/auth/tenantauthswitch/**').as('tenantAuthSwitch');
    cy.window().then((win) => { cy.stub(win, 'open').as('windowOpen'); });
    cy.get("button[name='configure_tenant']").first().click();

    cy.wait('@tenantAuthSwitch').then((interception: any) => {
      const redirectUrl = interception.response.body.redirect;
      cy.get('@windowOpen').should('be.calledWith', redirectUrl);
      cy.visit(redirectUrl);
    });

    cy.get("#admin_settings").click();
    cy.get("textarea[name='nodeResolver.dataModel.footer']").should("be.visible").type("dummy_footer");
    cy.get("#save_settings").click();
    cy.get('[data-cy="advanced"]').click().should("be.visible").click();
    cy.get('input[name="disable_submissions"]').click();
    cy.get('input[name="node.dataModel.pgp"]').click();
    cy.get("#save").click();
  });

  it("should add a new tenant from the profile, verify that variables change in the tenant, and update the tenant's variables", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click().should("be.visible").click();
    add_profile("Platform E", true);

    cy.intercept('GET', '/api/auth/tenantauthswitch/**').as('tenantAuthSwitch');
    cy.window().then((win: any) => {
      if (win.open.restore) {
        win.open.restore();
      }
      cy.stub(win, 'open').as('windowOpen');
    });

    cy.get("button[name='configure_tenant']").last().click();
    cy.wait('@tenantAuthSwitch').then((interception: any) => {
      const redirectUrl = interception.response.body.redirect;
      cy.get('@windowOpen').should('be.calledWith', redirectUrl);
      cy.visit(redirectUrl);
    });
    cy.get("#admin_settings").click();
    cy.get("textarea[name='nodeResolver.dataModel.footer']").should("be.visible").clear();
    cy.get("#save_settings").click();
    cy.get('[data-cy="advanced"]').click().should("be.visible").click();
    cy.get('input[name="disable_submissions"]').should('be.checked');
    cy.get('input[name="node.dataModel.pgp"]').should('be.checked');

    cy.get('input[name="disable_submissions"]').click();
    cy.get('input[name="node.dataModel.pgp"]').click();
    cy.get("#save").click();
    cy.logout();
  });
});
