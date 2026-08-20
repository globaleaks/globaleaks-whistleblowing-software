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

  const create_invite = (organizationName: string, email: string, alias: string) => {
    cy.intercept("POST", "/api/admin/invites").as(alias);
    cy.get('[data-cy="invite-organization-name"]').clear().type(organizationName);
    cy.get('[data-cy="invite-email"]').clear().type(email);
    cy.get('[data-cy="create-invite"]').click();
    return cy.wait(`@${alias}`).then((interception: any) => {
      cy.contains('[data-cy="invite-row"]', organizationName).should("exist");
      return cy.wrap(interception);
    });
  };

  const set_signup_enabled = (enabled: boolean) => {
    cy.get('[data-cy="options"]').should("be.visible").click();
    cy.get('input[name="enable_signup"]').then(($input) => {
      if ($input.is(":checked") !== enabled) {
        cy.wrap($input).click();
      }
    });
    cy.get("#save").click();
  };

  it("should add, configure and delete tenant", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");

    add_tenant("Platform A");
    add_tenant("Platform B");
    add_tenant("Platform C");

    cy.takeScreenshot("admin/sites_management_sites");

    cy.get("button[name='delete_tenant']").last().click();

    cy.get("#modal-action-ok").click();

    cy.get("button[name='configure_tenant']").last().click();

    cy.get('[data-cy="options"]').click();
    cy.takeScreenshot("admin/sites_management_options");
    cy.logout();
  });

  it("should back up and import a tenant", () => {
    const tenantName = "Tenant Backup";
    const profileName = "Backup Recipient Profile";
    const userName = "Backup Recipient";
    const userEmail = "backup-recipient@example.org";
    const footerText = "Tenant backup footer";
    const backupFilename = `${tenantName}.tenant-backup.tar.gz`;
    const backupPath = `cypress/downloads/${backupFilename}`;
    const configureTenant = () => {
      cy.intercept("GET", "/api/auth/tenantauthswitch/**").as("tenantAuthSwitch");
      cy.window().then((win: any) => {
        if (win.open.restore) {
          win.open.restore();
        }
        cy.stub(win, "open").as("windowOpen");
      });
      cy.contains(".config-item", tenantName)
        .find("button[name='configure_tenant']")
        .click();
      cy.wait("@tenantAuthSwitch").then((interception: any) => {
        const redirectUrl = interception.response.body.redirect;
        cy.get("@windowOpen").should("be.calledWith", redirectUrl);
        cy.visit(redirectUrl);
      });
    };

    cy.login_admin();
    cy.visit("/#/admin/sites");

    add_tenant(tenantName);
    configureTenant();

    cy.intercept("PUT", "**/api/admin/node").as("updateTenantSettings");
    cy.get("#admin_settings").click();
    cy.get("#node-footer").clear().type(footerText);
    cy.get("#save_settings").click();
    cy.wait("@updateTenantSettings");

    cy.get('[data-cy="advanced"]').click();
    cy.get('input[name="disable_submissions"]').check();
    cy.get("#scoring_system").check();
    cy.get("#save").click();
    cy.wait("@updateTenantSettings");

    cy.get("#admin_users").click();
    cy.get('[data-cy="profiles"]').click();
    cy.get(".show-add-profile-btn").click();
    cy.get('select[name="role"]').select("receiver");
    cy.get('input[name="name"]').clear().type(profileName);
    cy.get("#add-btn").click();
    cy.get(".profileList").contains(profileName).should("exist");

    cy.get('[data-cy="users"]').click();
    cy.get(".show-add-user-btn").click();
    cy.get('select[name="profile"]').select(profileName);
    cy.get('input[name="username"]').clear().type(userName);
    cy.get('input[name="name"]').clear().type(userName);
    cy.get('input[name="email"]').clear().type(userEmail);
    cy.get("#add-btn").click();
    cy.get(".userList").contains(userName).should("exist");

    cy.visit("/#/admin/sites");
    cy.contains(".config-item", tenantName).should("exist");

    cy.intercept("GET", "/api/admin/tenants/*/backup").as("backupTenant");
    cy.contains(".config-item", tenantName)
      .find("button[name='backup_tenant']")
      .click();
    cy.wait("@backupTenant", {timeout: 120000});
    cy.readFile(backupPath, null, {timeout: 120000}).should("have.length.greaterThan", 0);

    cy.intercept("DELETE", "/api/admin/tenants/*").as("deleteTenant");
    cy.contains(".config-item", tenantName)
      .find("button[name='delete_tenant']")
      .click();
    cy.get("#modal-action-ok").should("not.be.disabled").click();
    cy.wait("@deleteTenant");
    cy.contains(".config-item", tenantName).should("not.exist");

    cy.intercept("POST", "/api/admin/tenants/backup/import*").as("restoreTenant");
    cy.readFile(backupPath, null).then((backup) => {
      cy.get("#tenant-backup-import").selectFile({
        contents: backup,
        fileName: backupFilename,
        mimeType: "application/gzip"
      }, {force: true});
    });
    cy.wait("@restoreTenant", {timeout: 120000});
    cy.get('[data-cy="page-loader-overlay"]', {timeout: 120000}).should("not.exist");

    cy.contains(".config-item", tenantName, {timeout: 120000}).should("exist");
    configureTenant();

    cy.get("#admin_settings").click();
    cy.get("#node-footer").should("have.value", footerText);
    cy.get('[data-cy="advanced"]').click();
    cy.get('input[name="disable_submissions"]').should("be.checked");
    cy.get("#scoring_system").should("be.checked");

    cy.get("#admin_users").click();
    cy.get(".userList").contains(userName).should("exist");
    cy.get('[data-cy="profiles"]').click();
    cy.get(".profileList").contains(profileName).should("exist");

    cy.visit("/#/admin/sites");
    cy.contains(".config-item", tenantName)
      .find("button[name='delete_tenant']")
      .click();
    cy.get("#modal-action-ok").should("not.be.disabled").click();
    cy.wait("@deleteTenant");

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
    cy.get('[data-cy="advanced"]').click().should("be.visible").click();
    cy.get('input[name="disable_submissions"]').should('be.checked');
    cy.get('input[name="node.dataModel.pgp"]').should('be.checked');

    cy.get('input[name="disable_submissions"]').click();
    cy.get('input[name="node.dataModel.pgp"]').click();
    cy.get("#save").click();
    cy.logout();
  });

  it("should create, delete and accept registration invites", () => {
    let signupWasEnabled = false;

    cy.login_admin();
    cy.visit("/#/admin/sites");

    cy.get('[data-cy="options"]').should("be.visible").click();
    cy.get('input[name="enable_signup"]').then(($input) => {
      signupWasEnabled = $input.is(":checked");
      if (!signupWasEnabled) {
        cy.wrap($input).click();
        cy.get("#save").click();
      }
    });

    cy.get('[data-cy="invites"]').should("be.visible").click();

    create_invite("Pending Registration", "pending-registration@example.org", "pendingInvite");

    cy.intercept("DELETE", "/api/admin/invites/**").as("deleteInvite");
    cy.contains('[data-cy="invite-row"]', "Pending Registration").within(() => {
      cy.contains("invited").should("exist");
      cy.get('[data-cy="delete-invite"]').click();
    });
    cy.wait("@deleteInvite");

    cy.contains('[data-cy="invite-row"]', "Pending Registration").should("not.exist");

    create_invite("Accepted Registration", "accepted-registration@example.org", "acceptedInvite").then((interception: any) => {
      const token = interception.response.body.token;

      return cy.request("POST", "/api/signup", {
        token: token,
        subdomain: "",
        name: "Invite",
        surname: "Registrant",
        role: "",
        phone: "",
        email: "accepted-registration@example.org",
        organization_name: "",
        organization_tax_code: "",
        organization_vat_code: "",
        organization_location: "",
        tos1: true,
        tos2: false
      });
    });

    cy.visit("/#/admin/sites");
    cy.get('[data-cy="invites"]').should("be.visible").click();
    cy.get('[data-cy="sites"]').should("be.visible").click();
    cy.wait(1000);
    cy.get('[data-cy="invites"]').should("be.visible").click();

    cy.contains('[data-cy="invite-row"]', "Accepted Registration", { timeout: 20000 }).should("be.visible").within(() => {
      cy.contains("accepted").should("exist");
      cy.get('[data-cy="delete-invite"]').should("not.exist");
    });
    cy.contains('[data-cy="invite-row"]', "Accepted Registration").click();

    cy.get('[data-cy="registration-details"]').within(() => {
      cy.contains("Invite").should("exist");
      cy.contains("Registrant").should("exist");
      cy.contains("accepted-registration@example.org").should("exist");
    });

    cy.then(() => {
      if (!signupWasEnabled) {
        set_signup_enabled(false);
      }
    });

    cy.logout();
  });
});
