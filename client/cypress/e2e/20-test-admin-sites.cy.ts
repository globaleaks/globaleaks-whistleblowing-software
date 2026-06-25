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

  const configure_profile_tenant = (name: string) => {
    cy.contains("form", name).within(() => {
      cy.get("button[name='configure_tenant']").click();
    });
  };

  const configure_site_tenant = (name: string) => {
    cy.contains("form", name).within(() => {
      cy.get("button[name='configure_tenant']").click();
    });
  };

  const visit_configured_tenant = () => {
    return cy.wait('@tenantAuthSwitch').then((interception: any) => {
      const redirectUrl = interception.response.body.redirect;
      const tenantUrl = redirectUrl.split("#")[0].replace(/\/$/, "");

      return cy.get('@windowOpen')
        .should('be.calledWith', redirectUrl)
        .then(() => cy.visit(redirectUrl))
        .then(() => tenantUrl);
    });
  };

  const create_forwarding_recipient_profile = (tenantUrl: string, profileName: string) => {
    cy.get("#admin_users").click();
    cy.get('[data-cy="profiles"]').click().should("be.visible").click();
    cy.get(".show-add-profile-btn").click();
    cy.get('select[name="role"]').select("receiver");
    cy.get('input[name="name"]').clear().type(profileName);
    cy.get("#add-btn").click();

    cy.contains(".profileList", profileName).within(() => {
      cy.get('button[name="edit_profile"]').click();
      cy.get('input[name="can_forward_reports"]').check();
      cy.get('input[name="can_request_forward"]').check();
      cy.get("#save_profile").click();
    });
  };

  const create_recipient_from_profile = (tenantUrl: string, profileName: string, recipientName: string) => {
    cy.visit(`${tenantUrl}/#/admin/users`);
    cy.get('[data-cy="users"]').click().should("be.visible").click();
    cy.get(".show-add-user-btn").click();
    cy.get('select[name="profile"]').select(profileName);
    cy.get('input[name="username"]').clear().type(recipientName);
    cy.get('input[name="name"]').clear().type(recipientName);
    cy.get('input[name="email"]').clear().type(`${recipientName.toLowerCase().replace(/\s+/g, "-")}@example.org`);
    cy.get("#add-btn").click();
    cy.contains(".userList", recipientName).should("exist");
  };

  const set_recipient_password = (tenantUrl: string, recipientName: string) => {
    cy.visit(`${tenantUrl}/#/admin/users`);
    cy.intercept("PUT", `${tenantUrl}/api/admin/config`).as("setRecipientPassword");
    cy.contains(".userList", recipientName).within(() => {
      cy.get('button[name="edit_user"]').click();
      cy.get("#set_password").first().click();
      cy.get('input[name="password"]').clear().type(Cypress.env("init_password"));
      cy.get("#setPasswordButton").should("be.visible").click();
    });
    cy.wait("@setRecipientPassword").its("response.statusCode").should("be.within", 200, 299);
  };

  const complete_recipient_first_login = (tenantUrl: string, recipientName: string) => {
    cy.logout();
    cy.login_receiver(recipientName, Cypress.env("init_password"), `${tenantUrl}/#/login`, true);
    cy.get('[name="changePasswordArgs.password"]').should("be.visible").type(Cypress.env("user_password"));
    cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
    cy.get('button[name="submit"]').click();
    cy.waitForUrl("/recipient/home");
    cy.logout();
  };

  const add_recipient_to_channel = (tenantUrl: string, channelName: string, recipientName: string, optional = false) => {
    cy.visit(`${tenantUrl}/#/admin/channels`);
    cy.get('form[name="editContext"]').should("have.length.greaterThan", 0).then(($channels) => {
      const channel = $channels.filter((_, element) => {
        const name = (element as HTMLElement).querySelector(".editorHeader .col-md-7 > span")?.textContent?.trim();
        return name === channelName;
      }).first();

      if (!channel.length) {
        expect(optional, `${channelName} channel`).to.eq(true);
        return;
      }

      cy.wrap(channel).within(() => {
        cy.get("#edit_context").click();
        cy.get(".selection-list").then(($list) => {
          if (!$list.text().includes(recipientName)) {
            cy.get(".add-receiver-btn").click();
            cy.get('ng-select[name="selected.value"]').click();
            cy.get('ng-select[name="selected.value"]').contains(recipientName).click();
          }
        });
        cy.get("#save_context").click();
      });
    });
  };

  const configure_forwarding_recipient = (tenantUrl: string, profileName: string, recipientName: string) => {
    create_forwarding_recipient_profile(tenantUrl, profileName);
    create_recipient_from_profile(tenantUrl, profileName, recipientName);
    set_recipient_password(tenantUrl, recipientName);
    add_recipient_to_channel(tenantUrl, "Default", recipientName);
    add_recipient_to_channel(tenantUrl, "Forward", recipientName);
    complete_recipient_first_login(tenantUrl, recipientName);
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

  it("should add and configure the profile tenant", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="profiles"]').click().should("be.visible").click();
    add_profile("Platform D");

    cy.intercept('GET', '/api/auth/tenantauthswitch/**').as('tenantAuthSwitch');
    cy.window().then((win) => { cy.stub(win, 'open').as('windowOpen'); });
    configure_profile_tenant("Platform D");
    visit_configured_tenant();

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

    configure_site_tenant("Platform E");
    visit_configured_tenant().then((tenantUrl: string) => {
      cy.get("#admin_settings").click();
      cy.get('[data-cy="advanced"]').click().should("be.visible").click();
      cy.get('input[name="disable_submissions"]').should('be.checked');
      cy.get('input[name="node.dataModel.pgp"]').should('be.checked');

      cy.get('input[name="disable_submissions"]').click();
      cy.get('input[name="node.dataModel.pgp"]').click();
      cy.get("#save").click();
      cy.logout();
    });
  });

  it("should configure forwarding recipients for two profile tenants", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click().should("be.visible").click();
    add_tenant("Platform F");
    add_tenant("Platform G");

    cy.intercept('GET', '/api/auth/tenantauthswitch/**').as('tenantAuthSwitch');
    cy.window().then((win: any) => {
      if (win.open.restore) {
        win.open.restore();
      }
      cy.stub(win, 'open').as('windowOpen');
    });

    configure_site_tenant("Platform F");
    visit_configured_tenant().then((tenantUrl: string) => {
      configure_forwarding_recipient(tenantUrl, "Platform F Forwarding Profile", "Platform F Recipient");
    });

    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click().should("be.visible").click();
    cy.window().then((win: any) => {
      if (win.open.restore) {
        win.open.restore();
      }
      cy.stub(win, 'open').as('windowOpen');
    });
    configure_site_tenant("Platform G");
    visit_configured_tenant().then((tenantUrl: string) => {
      configure_forwarding_recipient(tenantUrl, "Platform G Forwarding Profile", "Platform G Recipient");
    });
  });
});
