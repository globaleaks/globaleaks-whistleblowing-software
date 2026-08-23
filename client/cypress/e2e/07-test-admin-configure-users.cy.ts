describe("admin add, configure, and delete users", () => {
  const new_users = [
    {
      name: "Recipient",
      value:"receiver",
      address: "globaleaks-receiver1@mailinator.com",
    },
    {
      name: "Recipient2",
      value:"receiver",
      address: "globaleaks-receiver2@mailinator.com",
    },
    {
      name: "Recipient3",
      value:"receiver",
      address: "globaleaks-receiver3@mailinator.com",
    },
    {
      name: "Custodian",
      value:"custodian",
      address: "globaleaks-custodian1@mailinator.com",
    },
    {
      name: "Admin2",
      value:"admin",
      address: "globaleaks-admin2@mailinator.com",
    },
    {
      name: "Analyst",
      value:"analyst",
      address: "globaleaks-analyst1@mailinator.com",
    },
  ];

  it("should add new users", () => {
    cy.login_admin();
    cy.visit("/#/admin/users");

    const make_account = (user:any) => {
      cy.get(".show-add-user-btn").click();
      cy.get('select[name="role"]').select(user.value);
      cy.get('input[name="username"]').clear().type(user.name);
      cy.get('input[name="name"]').clear().type(user.name);
      cy.get('input[name="email"]').clear().type(user.address);
      cy.get("#add-btn").click();
    };

    for (let i = 0; i < new_users.length; i++) {
      make_account(new_users[i]);
      cy.get(".userList").should('have.length', i+2);
    }
  });

  it("should grant permissions to the first recipient", () => {
    cy.login_admin();
    cy.visit("/#/admin/users");

    cy.get(".userList").eq(4).within(() => {
      cy.get("[data-action='edit']").click();
      cy.get('input[name="can_mask_information"]').click();
      cy.get('input[name="can_redact_information"]').click();
      cy.get('input[name="can_grant_access_to_reports"]').click();
      cy.get('input[name="can_transfer_access_to_reports"]').click();
      cy.get('input[name="can_delete_submission"]').click();
      cy.get('input[name="can_edit_general_settings"]').click();
      cy.get("[data-action='save']").click();
    });
  });

  it("should be able to send a password reset link to a user", () => {
    cy.login_admin();
    cy.visit("/#/admin/users");

    // Pick the first non-admin user and trigger the reset/activation link.
    // The administrator must confirm the operation with their own password;
    // sending the link does not alter the user's current password.
    cy.get(".userList").eq(1).find("[data-action='edit']").should("be.visible").click();
    cy.get(".userList").eq(1).find("#send_reset_link").should("be.visible").click();

    cy.get("[name='secret']").should("be.visible").clear().type(Cypress.env("user_password"));
    cy.get("#confirm").click();

    cy.logout();
  });

  it("should reset users' passwords and store the generated credentials", () => {
    cy.login_admin();
    cy.visit("/#/admin/users");

    // The administrator triggers a password reset for each user. The new
    // password is generated client-side and only revealed in a modal after the
    // change has been confirmed and applied. We capture each generated password
    // and keep it in an in-memory store (shared across specs via cy.task) so the
    // subsequent first-login tests can use the real credentials, indexed by
    // username (see 08-test-users-first-login).
    let screenshotTaken = false;

    cy.get(".userList").its("length").then(userListLength => {
      for (let i = 0; i < userListLength; i++) {
        cy.get(".userList").eq(i).find("[data-action='edit']").should("be.visible").click();

        cy.get(".userList").eq(i).then($row => {
          // The administrator's own account does not expose a password reset.
          if (Cypress.$("#set_password", $row).length === 0) {
            return;
          }

          cy.wrap($row).find("#user-username-input").invoke("val").then(username => {
            cy.wrap($row).find("#set_password").should("be.visible").click();

            // Confirm the administrative operation with the admin password.
            cy.get("[name='secret']").should("be.visible").clear().type(Cypress.env("user_password"));
            cy.get("#confirm").click();

            // The generated password is shown but hidden by default.
            cy.get("#NewPassword").should("be.visible").and("have.attr", "type", "password");

            // The show/hide toggle reveals and re-hides the password.
            cy.get("#toggle-visibility").click();
            cy.get("#NewPassword").should("have.attr", "type", "text");
            if (!screenshotTaken) {
              cy.takeScreenshot("admin/users_password_reset", ".modal-dialog");
              cy.then(() => { screenshotTaken = true; });
            }
            cy.get("#toggle-visibility").click();
            cy.get("#NewPassword").should("have.attr", "type", "password");

            // Capture the generated password for the user's first login.
            cy.get("#NewPassword").invoke("val").then(password => {
              cy.task("storeUserPassword", {username: String(username), password: String(password)});
            });

            cy.get("#close").click();
          });
        });
      }
    });

    cy.logout();
  });

});
