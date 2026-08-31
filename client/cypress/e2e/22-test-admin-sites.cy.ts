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

  // Enabling the accreditation adds a tab and the strip goes back to the first one: reopen the
  // options before saving
  const set_signup_enabled = (enabled: boolean) => {
    cy.get('[data-cy="options"]').click();
    cy.get('input[name="enable_signup"]').then(($input) => {
      if ($input.is(":checked") !== enabled) {
        cy.wrap($input).click();
        cy.get('[data-cy="options"]').click();
      }
    });
    cy.get("#save").click();
  };

  const enter_tenant = (name: string) => {
    cy.contains("form", name).within(() => {
      cy.get("button[name='configure_tenant']").click();
    });
  };

  const configure_profile_tenant = (name: string) => {
    enter_tenant(name);
  };

  const configure_site_tenant = (name: string) => {
    enter_tenant(name);
  };

  const visit_configured_tenant = () => {
    return cy.wait('@tenantAuthSwitch').then((interception: any) => {
      const redirectUrl = interception.response.body.redirect;
      const tenantUrl = redirectUrl.split("#")[0].replace(/\/$/, "");

      return cy.get('@windowOpen')
        .should('be.calledWith', redirectUrl)
        .then(() => cy.visit(redirectUrl))
        .then(() => cy.waitForUrl("/admin/home"))
        .then(() => tenantUrl);
    });
  };

  // A recipient carries its own reports to another organization and needs the permission; a
  // transmitter files on other sites and holds no report of its own
  const create_transmitting_recipient_profile = (tenantUrl: string, profileName: string, role: string) => {
    cy.get("#admin_users").click();
    cy.get('[data-cy="profiles"]').click();
    cy.get(".show-add-profile-btn").click();
    cy.get('select[name="role"]').select(role);
    cy.get('input[name="name"]').clear().type(profileName);
    cy.get("#add-btn").click();

    if (role !== "receiver") {
      return;
    }

    cy.contains(".profileList", profileName).within(() => {
      // the card expands from its title: there is no edit button
      cy.get(".editorTitle").click();
      // the checkbox binds its name through NgModel: reached by its label
      cy.contains(".permission-group-items .form-group", "Send communication to other organizations").find("input").check();
      cy.get("#save_profile").click();
    });
  };

  const create_recipient_from_profile = (tenantUrl: string, profileName: string, recipientName: string) => {
    cy.visit(`${tenantUrl}/#/admin/users`);
    cy.get('[data-cy="users"]').click();
    cy.get(".show-add-user-btn").click();
    cy.get('select[name="profile"]').select(profileName);
    cy.get('input[name="username"]').clear().type(recipientName);
    cy.get('input[name="name"]').clear().type(recipientName);
    cy.get('input[name="email"]').clear().type(`${recipientName.toLowerCase().replace(/\s+/g, "-")}@example.org`);
    cy.get("#add-btn").click();
    cy.contains(".userList", recipientName).should("exist");
  };

  // the generated password is shown only in the modal: read it there for the first login
  const generatedPasswords: Record<string, string> = {};

  const set_recipient_password = (tenantUrl: string, recipientName: string) => {
    // visiting the address already displayed performs no navigation: leave the platform first
    cy.visit(`${tenantUrl}/#/admin/home`);
    cy.visit(`${tenantUrl}/#/admin/users`);
    cy.get('[data-cy="users"]').click();
    // wait for the list holding the account, not for the request that fills it
    cy.waitForPageIdle();
    cy.contains(".userList", recipientName).should("exist");
    cy.intercept("PUT", `${tenantUrl}/api/admin/config`).as("setRecipientPassword");
    // no assertion breaks the chain, so the query re-runs if the row is redrawn
    cy.contains(".userList", recipientName).find("[data-action='edit']").click();
    cy.contains(".userList", recipientName).find("#set_password").first().click();

    cy.get("[name='secret']").should("be.visible").clear().type(Cypress.env("user_password"));
    cy.get("#confirm").click();
    cy.wait("@setRecipientPassword").its("response.statusCode").should("be.within", 200, 299);

    cy.get("#NewPassword").should("be.visible").invoke("val").then(password => {
      generatedPasswords[recipientName] = String(password);
    });
    cy.get("#close").click();
  };

  const complete_recipient_first_login = (tenantUrl: string, recipientName: string) => {
    cy.logout();
    cy.then(() => {
      cy.login_receiver(recipientName, generatedPasswords[recipientName], `${tenantUrl}/#/login`, true);
      cy.get('[name="changePasswordArgs.password"]').should("be.visible").type(Cypress.env("user_password"));
      cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
      cy.get('button[name="submit"]').click();
      cy.waitForUrl("/recipient/home");
      cy.logout();
    });
  };

  // A channel names user profiles, not users
  const add_profile_to_channel = (tenantUrl: string, channelName: string, profileName: string) => {
    cy.visit(`${tenantUrl}/#/admin/channels`);
    // await the channel by name: a snapshot taken while rendering missed channels
    cy.contains("form[name='editContext']", channelName).should("exist").within(() => {
      cy.get("[data-action='edit']").click();
      cy.get(".selection-list").then(($list) => {
        if (!$list.text().includes(profileName)) {
          cy.get(".add-receiver-btn").click();
          cy.get('ng-select[name="selected.value"]').click();
          cy.get('ng-select[name="selected.value"]').contains(profileName).click();
        }
      });
      cy.get("[data-action='save']").click();
    });
  };

  const configure_transmitting_recipient = (tenantUrl: string, profileName: string, recipientName: string, role = "receiver") => {
    create_transmitting_recipient_profile(tenantUrl, profileName, role);
    create_recipient_from_profile(tenantUrl, profileName, recipientName);
    set_recipient_password(tenantUrl, recipientName);
    // only a recipient receives on a channel
    if (role === "receiver") {
      add_profile_to_channel(tenantUrl, "Default", profileName);
    }
    complete_recipient_first_login(tenantUrl, recipientName);
  };

  it("should add, configure and delete tenant", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");

    add_tenant("Platform A");
    add_tenant("Platform B");
    add_tenant("Platform C");

    cy.takeScreenshot("admin/sites_management_sites");

    cy.get(".tenant [data-action='delete']").last().click();

    cy.get(".modal-title").should("be.visible");

    // the confirm button is inert while the modal is still counting
    cy.get("#modal-action-ok").should("not.be.disabled").click();
    cy.get(".modal [type='password']").should("be.visible").type(Cypress.env("user_password"));
    cy.get(".modal .btn-primary").click();

    cy.get("button[name='configure_tenant']").last().click();

    cy.get('[data-cy="options"]').click();
    cy.takeScreenshot("admin/sites_management_options");
    cy.logout();
  });

  it("should add and configure the profile tenant", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="profiles"]').click();
    add_profile("Platform D");

    cy.intercept('GET', '/api/auth/tenantauthswitch/**').as('tenantAuthSwitch');
    cy.window().then((win) => { cy.stub(win, 'open').as('windowOpen'); });
    configure_profile_tenant("Platform D");
    visit_configured_tenant();

    cy.get("#admin_settings").click();
    cy.get('[data-cy="advanced"]').click();
    cy.get('input[name="disable_submissions"]').click();
    cy.get('input[name="node.dataModel.pgp"]').click();
    cy.get("#save").click();
  });

  it("should add a new tenant from the profile, verify that variables change in the tenant, and update the tenant's variables", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click();
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
      cy.get('[data-cy="advanced"]').click();
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
    cy.get('[data-cy="sites"]').click();
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
    cy.get('[data-cy="sites"]').click();
    cy.window().then((win: any) => {
      if (win.open.restore) {
        win.open.restore();
      }
      cy.stub(win, 'open').as('windowOpen');
    });
    configure_site_tenant("Platform G");
    visit_configured_tenant().then((tenantUrl: string) => {
      configure_transmitting_recipient(tenantUrl, "Platform G Transmission Profile", "Platform G Recipient", "transmitter");
    });
  });

  it("should create, delete and accept registration invites", () => {
    let signupWasEnabled = false;

    cy.login_admin();
    cy.visit("/#/admin/sites");

    cy.get('[data-cy="options"]').click();
    cy.get('input[name="enable_signup"]').then(($input) => {
      signupWasEnabled = $input.is(":checked");
      if (!signupWasEnabled) {
        cy.wrap($input).click();
        // the registrations tab appears and the strip resets: reopen the options to save
        cy.get('[data-cy="options"]').click();
        cy.get("#save").click();
      }
    });

    cy.get('[data-cy="invites"]').click();

    create_invite("Pending Registration", "pending-registration@example.org", "pendingInvite");

    cy.takeScreenshot("admin/sites_invites");

    cy.intercept("DELETE", "/api/admin/invites/**").as("deleteInvite");
    cy.contains('[data-cy="invite-row"]', "Pending Registration").within(() => {
      cy.contains("invited").should("exist");
      cy.get('[data-cy="delete-invite"]').click();
    });
    cy.wait("@deleteInvite");

    cy.contains('[data-cy="invite-row"]', "Pending Registration").should("not.exist");

    create_invite("Accepted Registration", "accepted-registration@example.org", "acceptedInvite").then((interception: any) => {
      const token = interception.response.body.token;

      // the API refuses the request without the token the browser obtains: go through the page
      cy.visit(`/#/signup?token=${token}`);
      cy.get("#SignupForm").should("be.visible");

      cy.get('input[name="name"]').clear().type("Invite");
      cy.get('input[name="surname"]').clear().type("Registrant");
      cy.get('input[name="mail_address"]').clear().type("accepted-registration@example.org");
      cy.get('input[name="email"]').clear().type("accepted-registration@example.org");

      // fill what is on display; the organization name comes from the invitation
      const details: Record<string, string> = {
        "signup-subdomain": "invited",
        "signup-organization-location": "Roma",
        "signup-organization-phone": "0123456789",
        "signup-organization-tax-code": "AAABBB00A00A000A",
        "signup-organization-vat-code": "00000000000"
      };

      cy.get("body").then(($body) => {
        Object.entries(details).forEach(([id, value]) => {
          if ($body.find(`#${id}`).length) {
            cy.get(`#${id}`).clear().type(value);
          }
        });

        if ($body.find('#SignupForm input[type="checkbox"]').length) {
          cy.get('#SignupForm input[type="checkbox"]').check({force: true});
        }
      });

      // the registration is awaited: leaving the page while it is still in flight
      // reads the invitations before it lands, and finds the invitation still open
      cy.intercept("POST", "**/api/signup").as("signup");
      cy.get(".ButtonNext").click();
      return cy.wait("@signup").its("response.statusCode").should("eq", 201);
    });

    cy.visit("/#/admin/sites");
    cy.get('[data-cy="invites"]').click();

    // accepted: no longer withdrawable; the state depends on whether new sites are authorized
    // automatically
    cy.contains('[data-cy="invite-row"]', "Accepted Registration", { timeout: 20000 }).should("be.visible").within(() => {
      cy.contains("invited").should("not.exist");
      cy.get('[data-cy="delete-invite"]').should("not.exist");
    });
    // the card opens on its title button, the left half of the header: clicking elsewhere expands
    // nothing
    cy.contains('[data-cy="invite-row"]', "Accepted Registration").find(".editorTitle").click();

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
  // An exchange relates one pair: type, mode and the channel of the destination it runs through
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

  // The configuration is written inside the row of the exchange, named by site and type
  const configure_exchange = (type: string, name: string, configure: () => void) => {
    // the exchange just established is already open: toggling would close it
    cy.get("tr.exchange-row")
      .filter(`:contains("${name}")`)
      .filter(`:contains("${type}")`)
      .first()
      .then(($row) => {
        if (!$row.hasClass("expandable-row-open")) {
          cy.wrap($row).find('[data-action="toggle"]').click();
        }
      });
    cy.get("tr.exchange-detail").within(configure);
  };

  // the Authority establishes the exchanges the other organizations communicate and file
  // through. The questionnaire of an exchange composes what runs through it
  it("should relate the sites and run the exchanges through their channels", () => {
    cy.login_admin();

    cy.visit("/#/admin/sites");
    cy.get('[data-cy="exchanges"]').click().click();

    // photographed filled in: sides and channel appear only after the previous choices
    cy.get(".add-exchange-btn").click();
    cy.get('select[name="exchange-type"]').select("communication");
    cy.get('select[name="exchange-mode"]').select("site-site");
    cy.get('select[name="exchange-from"]').select("Platform F");
    cy.get('select[name="exchange-to"]').select("GLOBALEAKS");
    cy.get('select[name="exchange-channel"]').select("new");
    cy.get('input[name="exchange-channel-name"]').type("Exchange channel");

    cy.takeScreenshot("admin/sites_exchanges_add");
    cy.takeScreenshot("admin/sites_exchanges_add_detail", ".col-md-6");

    // the channel of the exchanges is created by the first exchange; the later ones run through it
    cy.get("#add-exchange").click();
    add_exchange("communication", "site-site", "Platform G", "GLOBALEAKS",
                 "Exchange channel");

    // and one of them files its reports on it, upon a request
    add_exchange("transmission", "site-site", "Platform G", "GLOBALEAKS",
                 "Exchange channel");

    cy.get("tr.exchange-row").should("have.length", 3);

    cy.takeScreenshot("admin/sites_exchanges");
    cy.takeScreenshot("admin/sites_exchanges_detail", "table.table");

    // the destination demands an authorization: a request is filed first, with a questionnaire of
    // its own
    configure_exchange("Transmission", "Platform G", () => {
      // the questionnaire of the exchange replaces the one of the channel
      cy.get('select[name="exchange-questionnaire"]').find("option").should("have.length.greaterThan", 1);
      cy.get('select[name="exchange-questionnaire"]').select(1);

      cy.get('input[name="exchange-request-authorization"]').check();
      // the request uses the default questionnaire, the one the suite can answer
      cy.get('select[name="exchange-request-questionnaire"]').find("option").should("have.length.greaterThan", 0);
      cy.get('select[name="exchange-request-questionnaire"]').select(0);

      // await the save, so a refusal is not mistaken for a configuration performed
      cy.intercept("PUT", "**/api/admin/exchanges/*").as("saveExchange");
      cy.get('[data-action="save"]').click();
    });

    cy.wait("@saveExchange").its("response.statusCode").should("eq", 202);

    // both questionnaires are named in the row of the exchange, reopened to be photographed
    configure_exchange("Transmission", "Platform G", () => {
      cy.get('select[name="exchange-request-questionnaire"]').should("be.visible");
    });
    cy.takeScreenshot("admin/sites_exchanges_questionnaires");

    // a capture changes the viewport and closes the open row: reopen it
    configure_exchange("Transmission", "Platform G", () => {
      cy.get('select[name="exchange-request-questionnaire"]').should("be.visible");
    });
    cy.takeScreenshot("admin/sites_exchanges_questionnaires_detail", '[data-cy="exchange-details"]');

    // the recipients taking part in the exchanges are named on the channel
    cy.visit("/#/admin/channels");
    cy.contains("form[name='editContext']", "Exchange channel").within(() => {
      cy.get("[data-action='edit']").click();
      cy.get(".add-receiver-btn").click();
      cy.get('ng-select[name="selected.value"]').click();
      cy.get('ng-select[name="selected.value"]').contains("Profile1").click();
      cy.get("[data-action='save']").click();
    });

    cy.visit("/#/admin/sites");
    cy.get('[data-cy="exchanges"]').click().click();
    cy.contains("tr.exchange-row", "Exchange channel").should("exist");

    cy.logout();
  });
});

// A profile is the template a site is built from: created, configured, exported, deleted and
// imported here
describe("the life of a tenant profile", () => {
  const profileName = "Model profile";
  const channelName = "Channel of the model profile";
  const userProfileName = "Recipients of the model profile";
  const exportedProfile = `cypress/downloads/${profileName}.json`;

  const openProfiles = () => {
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="profiles"]').click();
  };

  // the actions share identifiers across cards: reached inside the card of the profile
  const profileCard = (name: string) => cy.contains("src-collapsible-card", name);

  it("should create a tenant profile", () => {
    cy.login_admin();
    openProfiles();

    cy.get(".show-add-profile-btn").click();
    cy.get("[name='newTenant.name']").type(profileName);
    cy.get("#add-btn").click();

    profileCard(profileName).should("exist");
    cy.logout();
  });

  it("should configure the profile with a user profile, a channel and a default account", () => {
    cy.login_admin();
    openProfiles();

    cy.intercept("GET", "/api/auth/tenantauthswitch/**").as("tenantAuthSwitch");
    cy.window().then((win) => { cy.stub(win, "open").as("windowOpen"); });
    profileCard(profileName).within(() => {
      cy.get("#action-tenant-profile-configure").click();
    });
    cy.wait("@tenantAuthSwitch").then((interception: any) => {
      cy.visit(interception.response.body.redirect);
    });

    cy.get("#admin_users").click();
    cy.get('[data-cy="profiles"]').click();
    cy.get(".show-add-profile-btn").click();
    cy.get('select[name="role"]').select("receiver");
    cy.get('input[name="name"]').clear().type(userProfileName);
    cy.get("#add-btn").click();
    cy.contains(".profileList", userProfileName).should("exist");

    // a channel names user profiles, not users
    cy.get("#admin_channels").click();
    cy.get(".show-add-context-btn").click();
    cy.get("[name='new_context.name']").type(channelName);
    cy.get("#add-btn").click();

    // the editor renders only while the card is open, and a card just added may be open already
    cy.contains("form[name='editContext']", channelName).then(($form) => {
      if (!$form.find(".add-receiver-btn").length) {
        cy.wrap($form).find("[data-action='edit']").click();
      }
    });

    cy.contains("form[name='editContext']", channelName).within(() => {
      cy.get(".add-receiver-btn").click();
      cy.get('ng-select[name="selected.value"]').click();
      cy.get('ng-select[name="selected.value"]').contains(userProfileName).click();
      cy.get("[data-action='save']").click();
    });

    cy.get("#admin_settings").click();
    cy.get('[data-cy="advanced"]').click();
    cy.get("#default-user-profile-select").select(userProfileName);
    cy.get("#save").click();
  });

  it("should export the configured profile", () => {
    cy.login_admin();
    openProfiles();

    cy.takeScreenshot("admin/sites_profiles");
    cy.takeScreenshot("admin/sites_profiles_actions_detail", "src-collapsible-card:last .editorHeader");

    profileCard(profileName).within(() => {
      cy.get("#action-tenant-profile-export").click();
    });

    // the export carries the channel, the user profile that names it and the account
    cy.readFile(exportedProfile, {timeout: 20000}).then((exported: any) => {
      expect(exported.tenant.name).to.eq(profileName);
      expect(JSON.stringify(exported.contexts)).to.contain(channelName);
      expect(JSON.stringify(exported.user_profiles)).to.contain(userProfileName);
    });

    cy.logout();
  });

  it("should delete the exported profile", () => {
    cy.login_admin();
    openProfiles();

    profileCard(profileName).within(() => {
      cy.get("#action-tenant-profile-delete").click();
    });

    // the confirm button is inert while the modal is still counting
    cy.get("#modal-action-ok").should("not.be.disabled").click();
    cy.get(".modal [type='password']").should("be.visible").type(Cypress.env("user_password"));
    cy.get(".modal .btn-primary").click();

    cy.contains("src-collapsible-card", profileName).should("not.exist");
    cy.logout();
  });

  it("should import the exported profile back", () => {
    cy.login_admin();
    openProfiles();

    // the file input is hidden behind its label
    cy.get('input[type="file"]').selectFile(exportedProfile, {force: true});

    profileCard(profileName).should("exist");

    // what came back carries its channel and its user profile
    cy.intercept("GET", "/api/auth/tenantauthswitch/**").as("tenantAuthSwitch");
    cy.window().then((win) => { cy.stub(win, "open").as("windowOpen"); });
    profileCard(profileName).within(() => {
      cy.get("#action-tenant-profile-configure").click();
    });
    cy.wait("@tenantAuthSwitch").then((interception: any) => {
      cy.visit(interception.response.body.redirect);
    });

    cy.get("#admin_channels").click();
    cy.contains(channelName).should("exist");

    cy.get("#admin_users").click();
    cy.get('[data-cy="profiles"]').click();
    cy.contains(".profileList", userProfileName).should("exist");
  });

  it("should leave the platform as it found it", () => {
    // leave no extra profile behind: the later chapters depend on it
    cy.login_admin();
    openProfiles();

    profileCard(profileName).within(() => {
      cy.get("#action-tenant-profile-delete").click();
    });

    cy.get("#modal-action-ok").should("not.be.disabled").click();
    cy.get(".modal [type='password']").should("be.visible").type(Cypress.env("user_password"));
    cy.get(".modal .btn-primary").click();

    cy.contains("src-collapsible-card", profileName).should("not.exist");
    cy.logout();
  });
});
