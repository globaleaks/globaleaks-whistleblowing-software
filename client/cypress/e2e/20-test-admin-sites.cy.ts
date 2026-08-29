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
    cy.get('[data-cy="open-invite-modal"]').click();
    cy.get('[data-cy="invite-mail-template"]').should("not.have.value", "");
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

  const create_transmitting_recipient_profile = (tenantUrl: string, profileName: string) => {
    cy.get("#admin_users").click();
    cy.get('[data-cy="profiles"]').click().should("be.visible").click();
    cy.get(".show-add-profile-btn").click();
    cy.get('select[name="role"]').select("receiver");
    cy.get('input[name="name"]').clear().type(profileName);
    cy.get("#add-btn").click();

    cy.contains(".profileList", profileName).within(() => {
      cy.get('button[name="edit_profile"]').click();
      cy.get('input[name="can_send_communications"]').check();
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

  const configure_transmitting_recipient = (tenantUrl: string, profileName: string, recipientName: string) => {
    create_transmitting_recipient_profile(tenantUrl, profileName);
    create_recipient_from_profile(tenantUrl, profileName, recipientName);
    set_recipient_password(tenantUrl, recipientName);
    add_recipient_to_channel(tenantUrl, "Default", recipientName);
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
    cy.get(".modal [type='password']").type(Cypress.env("user_password"));
    cy.get(".modal .btn-primary").click();

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

  it("should configure transmission recipients for two profile tenants", () => {
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
      configure_transmitting_recipient(tenantUrl, "Platform F Transmission Profile", "Platform F Recipient");
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
      configure_transmitting_recipient(tenantUrl, "Platform G Transmission Profile", "Platform G Recipient");
    });
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

describe("admin configure exchanges", () => {
  // An exchange relates a single pair: the type says what the two sites
  // exchange, the mode what the two sides of the pair are made of, and the
  // channel of the destination it runs through is named here, where the
  // exchange is established
  const add_exchange = (type: string, mode: string, from: string, to: string,
                        channel: string, name?: string) => {
    cy.get(".add-exchange-btn").click();
    cy.get('select[name="exchange-type"]').select(type);
    cy.get('select[name="exchange-mode"]').select(mode);
    cy.get('select[name="exchange-from"]').select(from);
    cy.get('select[name="exchange-to"]').select(to);
    cy.get('select[name="exchange-channel"]').select(channel);

    if (name) {
      cy.get('input[name="exchange-channel-name"]').type(name);
    }

    cy.get("#add-exchange").click();
  };

  // The configuration of an exchange is written inside its own row: the row
  // is named by the site and by the type, since a pair exchanges on as many
  // exchanges as the channels it exchanges on
  const configure_exchange = (type: string, name: string, configure: () => void) => {
    cy.get("tr.exchange-row")
      .filter(`:contains("${name}")`)
      .filter(`:contains("${type}")`)
      .first()
      .find('[data-action="toggle"]')
      .click();
    cy.get("tr.exchange-detail").within(configure);
  };

  it("should relate the sites and run the exchanges through their channels", () => {
    cy.login_admin();

    cy.visit("/#/admin/sites");
    cy.get('[data-cy="exchanges"]').click().should("be.visible").click();

    // the two sites carry to the first one what their reports hold: a channel
    // of the exchanges is born of the first exchange running through it, and
    // the ones established afterwards run through the same one
    add_exchange("communication", "site-site", "Platform F", "GLOBALEAKS",
                 "new", "Exchange channel");
    add_exchange("communication", "site-site", "Platform G", "GLOBALEAKS",
                 "Exchange channel");

    // and one of them files its reports on it, upon a request
    add_exchange("transmission", "site-site", "Platform G", "GLOBALEAKS",
                 "Exchange channel");

    cy.get("tr.exchange-row").should("have.length", 3);

    // the destination demands an authorization before a report is entered on
    // it: what is filed first is a request, composed with a questionnaire of
    // its own
    configure_exchange("Transmission", "Platform G", () => {
      cy.get('input[name="exchange-request-authorization"]').check();
      cy.get('select[name="exchange-request-questionnaire"]').select(0);
      cy.get('[data-action="save"]').click();
    });

    // the recipients that take part in the exchanges are named on the channel,
    // where it lives
    cy.visit("/#/admin/channels");
    cy.contains("form[name='editContext']", "Exchange channel").within(() => {
      cy.get("[data-action='edit']").click();
      cy.get(".add-receiver-btn").click();
      cy.get('ng-select[name="selected.value"]').click();
      cy.get('ng-select[name="selected.value"]').contains("Recipient").click();
      cy.get("[data-action='save']").click();
    });

    // the exchanges are read back from the platform with the channel they run
    // through
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="exchanges"]').click().should("be.visible").click();
    cy.contains("tr.exchange-row", "Exchange channel").should("exist");

    cy.logout();
  });
});
