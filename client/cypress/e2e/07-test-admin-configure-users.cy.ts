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
  ];

  it("should add new users and profiles", () => {
    cy.login_admin();
    cy.visit("/#/admin/users");
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
    cy.visit("/#/admin/users");
    cy.get('[data-cy="profiles"]').click().should("be.visible").click();

    cy.get(".profileList").contains("Profile1").parents(".config-item").within(() => {
      cy.get('button[name="edit_profile"]').click();

      cy.get('input[name="can_mask_information"]').click();
      cy.get('input[name="can_redact_information"]').click();
      cy.get('input[name="can_grant_access_to_reports"]').click();
      cy.get('input[name="can_transfer_access_to_reports"]').click();
      cy.get('input[name="can_delete_submission"]').click();
      cy.get('input[name="can_edit_general_settings"]').click();
      cy.get("#save_profile").click();
    });
  });

  it("should configure users' passwords", () => {
    cy.login_admin();
    cy.visit("/#/admin/users");

    cy.get(".userList").its("length").then(userListLength => {
      const numberOfUsers = Math.min(userListLength, 7);
      for (let i = 1; i < numberOfUsers; i++) {
        cy.get(".userList").eq(i).within(() => {
          if (Cypress.$('button[name="edit_user"]').length > 0) {
            cy.get('button[name="edit_user"]').should('be.visible').click();
            cy.get("#set_password").first().click();
            cy.get('input[name="password"]').clear().type(Cypress.env("init_password"));
            cy.get('#setPasswordButton').should('be.visible').click();
          }
        });
      }
    });

    cy.logout();
  });

});

describe("Multiple role profile", () => {
  it("should add multiple role to the profile", () => {
    cy.login_admin();
    cy.visit("/#/admin/users");
    cy.get('[data-cy="profiles"]').click().should("be.visible").click();
    cy.get(".profileList").contains("Profile7 (Multi Role)").parents(".config-item").within(() => {
      cy.get('button[name="edit_profile"]').click();
      cy.get('ng-select').click();
      cy.get('.ng-dropdown-panel .ng-option').contains('Recipient').click();
      cy.get("#save_profile").click();
    });
  });

  it("should require password change upon successful authentication", () => {
    cy.login_receiver("Multi Role User", Cypress.env("init_password"), "#/login", true);
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
    cy.get('.modal-title').should('contain', 'Switch role');
    cy.get('ng-select').click();
    cy.get('.ng-dropdown-panel .ng-option').contains('Recipient').click();
    cy.get('#modal-action-ok').click();

    cy.url().should('include', '/recipient/home');
    cy.logout();
  });
})
