import {t} from "../support/i18n";
describe("admin add, configure, and delete users", () => {
  const new_users = [
    {
      name: "Recipient",
      value:"Profile1",
      address: "globaleaks-receiver1@mailinator.com",
    },
    {
      name: "Recipient2",
      value:"Profile2",
      address: "globaleaks-receiver2@mailinator.com",
    },
    {
      name: "Recipient3",
      value:"Profile3",
      address: "globaleaks-receiver3@mailinator.com",
    },
    {
      name: "Custodian",
      value:"Profile4",
      address: "globaleaks-custodian1@mailinator.com",
    },
    {
      name: "Admin2",
      value:"Profile5",
      address: "globaleaks-admin2@mailinator.com",
    },
    {
      name: "Analyst",
      value:"Profile6",
      address: "globaleaks-analyst1@mailinator.com",
    },
    {
      name: "Multi Role User",
      value:"Profile7 (Multi Role)",
      address: "globaleaks-multi-role-user@mailinator.com",
    },
    {
      name: "Auditor",
      value:"Profile8",
      address: "globaleaks-auditor1@mailinator.com",
    },
  ];

  const new_profiles = [
    {
      name: "Profile1",
      value:"receiver",
    },
    {
      name: "Profile2",
      value:"receiver",
    },
    {
      name: "Profile3",
      value:"receiver",
    },
    {
      name: "Profile4",
      value:"custodian",
    },
    {
      name: "Profile5",
      value:"admin",
    },
    {
      name: "Profile6",
      value:"analyst",
    },
    {
      name: "Profile7 (Multi Role)",
      value:"admin",
    },
    {
      name: "Profile8",
      value:"auditor",
    },
  ];

  it("should add new users and profiles", () => {
    cy.login_admin();
    cy.openAdminUsers();
    cy.get('[data-cy="profiles"]').click();

    const make_profile = (profile:any) => {
      cy.get(".show-add-profile-btn").click();
      cy.get('select[name="role"]').select(profile.value);
      cy.get('input[name="name"]').clear().type(profile.name);
      cy.get("#add-btn").click();
    };

    for (let i = 0; i < new_profiles.length; i++) {
      make_profile(new_profiles[i]);
      cy.get(".profileList").should('have.length', i+1);
    }

    cy.get('[data-cy="users"]').click();

    const make_account = (user:any) => {
      cy.get(".show-add-user-btn").click();
      cy.get('select[name="profile"]').select(user.value);
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
    cy.openAdminUsers();
    cy.get('[data-cy="profiles"]').click();

    cy.get(".profileList").should("be.visible");
    cy.takeScreenshot("admin/user_profiles");

    // The checkboxes bind their name through NgModel: reached by label
    const grant = (label: string) => {
      cy.contains(".permission-group-items .form-group", label).find("input").check();
    };

    cy.get(".profileList").contains("Profile1").parents(".config-item").within(() => {
      // the profile card is expanded from its title: the editor has no dedicated
      // edit button, only save, export and delete
      cy.get(".editorTitle").click();

      grant(t("Mask information"));
      grant(t("Redact information"));
      grant(t("Grant access to reports"));
      grant(t("Transfer access to reports"));
      grant(t("Delete reports"));
      grant(t("Settings"));
      grant(t("Send communication to other organizations"));
      cy.get("#save_profile").click();
    });
  });

  // Composing the statistical templates is a permission of its own
  it("should grant the analysts the composition of the statistical templates", () => {
    cy.login_admin();
    cy.openAdminUsers();
    cy.get('[data-cy="profiles"]').click();

    cy.get(".profileList").should("be.visible");

    cy.get(".profileList").contains("Profile6").parents(".config-item").within(() => {
      cy.get(".editorTitle").click();

      cy.contains(".permission-group-items .form-group", t("Templates")).find("input").check();
      cy.get("#save_profile").click();
    });
  });

  it("should be able to send a password reset link to a user", () => {
    cy.login_admin();
    cy.openAdminUsers();

    // Pick the first non-admin user and trigger the reset/activation link.
    // The administrator must confirm the operation with their own password;
    // sending the link does not alter the user's current password.
    // the chain is left unbroken by assertions, so that Cypress re-runs the
    // query when the row is redrawn between the lookup and the click
    cy.get(".userList").eq(1).find("[data-action='edit']").click();
    cy.get(".userList").eq(1).find("#send_reset_link").click();

    cy.get("[name='secret']").should("be.visible").clear().type(Cypress.env("user_password"));
    cy.get("#confirm").click();

    cy.logout();
  });

  // the administrator generates the credentials that are delivered to the
  // user; the replacement of the password upon the first access is covered by
  // the first login tests in 08-test-users-first-login.
  it("should reset users' passwords and store the generated credentials", () => {
    cy.login_admin();
    cy.openAdminUsers();

    // The administrator triggers a password reset for each user. The new
    // password is generated client-side and only revealed in a modal after the
    // change has been confirmed and applied. We capture each generated password
    // and keep it in an in-memory store (shared across specs via cy.task) so the
    // subsequent first-login tests can use the real credentials, indexed by
    // username (see 08-test-users-first-login).
    let screenshotTaken = false;

    cy.get(".userList").its("length").then(userListLength => {
      for (let i = 0; i < userListLength; i++) {
        cy.get(".userList").eq(i).find("[data-action='edit']").click();

        cy.get(".userList").eq(i).then($row => {
          // The administrator's own account does not expose a password reset.
          if (Cypress.$("#set_password", $row).length === 0) {
            return;
          }

          cy.get(".userList").eq(i).find("#user-username-input").invoke("val").then(username => {
            cy.get(".userList").eq(i).find("#set_password").click();

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

  // The modal that protects the deletion is exercised here on a user without data
  it("should show user stats in delete confirmation modal", () => {
    cy.login_admin();
    cy.openAdminUsers();

    cy.get(".userList").last().within(() => {
      // the buttons of a repeated row carry no id: they are reached by the
      // action they perform
      cy.get("[data-action='edit']").click();
      cy.get("[data-action='delete']").click();
    });

    cy.get('.modal-title').should('be.visible');

    cy.get('#modal-action-cancel').click();
    cy.get('.modal-title').should('not.exist');

    cy.logout();
  });

});

describe("Multiple role profile", () => {
  it("should add multiple role to the profile", () => {
    cy.login_admin();
    cy.openAdminUsers();
    cy.get('[data-cy="profiles"]').click();
    cy.get(".profileList").contains("Profile7 (Multi Role)").parents(".config-item").within(() => {
      // the profile card is expanded from its title: the editor has no dedicated
      // edit button, only save, export and delete
      cy.get(".editorTitle").click();
      // the selector of the roles is revealed by the Add button of its section
      cy.get(".add-role-btn").click();
      cy.get("#RoleAdder ng-select").click();
      cy.get('.ng-dropdown-panel .ng-option').contains('Recipient').click();
      cy.get("#save_profile").click();
    });
  });

  it("should require password change upon successful authentication", () => {
    // the credentials are the ones generated by the administrator above, not the
    // initial password: the platform generates them and reveals them once
    cy.task("getUsersPasswords").then((users_passwords: any) => {
      cy.login_receiver("Multi Role User", users_passwords["Multi Role User"], "#/login", true);
    });
    cy.get('[name="changePasswordArgs.password"]').should('be.visible').type(Cypress.env("user_password"));
    cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
    cy.get('button[name="submit"]').click();
    cy.url().should("include", "/admin/home");
    cy.logout();
  });

  it("should switch role from admin to recipient", () => {
    cy.login_admin('Multi Role User');
    cy.window().then((win) => {
      cy.stub(win, 'open').callsFake((url) => {
        win.location.href = url;
      });
    });

    cy.get("#SwitchRoleLink").click();
    cy.get('.modal-title').should('contain', t('Switch role'));
    cy.get('ng-select').click();
    cy.get('.ng-dropdown-panel .ng-option').contains('Recipient').click();
    cy.get('#modal-action-ok').click();

    cy.url().should('include', '/recipient/home');
    cy.logout();
  });
})
