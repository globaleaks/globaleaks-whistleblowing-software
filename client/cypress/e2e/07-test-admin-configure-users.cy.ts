describe("admin add, configure, and delete users", () => {
  const new_users = [
    {
      name: "Recipient",
      value:"receiver",
      address: "globaleaks-receiver1@mailinator.com",
      idp_id: "PRKPTR88H01L219U",
    },
    {
      name: "Recipient2",
      value:"receiver",
      address: "globaleaks-receiver2@mailinator.com",
      idp_id: "PRKPTR88H01L219U",
    },
    {
      name: "Recipient3",
      value:"receiver",
      address: "globaleaks-receiver3@mailinator.com",
      idp_id: "PRKPTR88H01L219U",
    },
    {
      name: "Custodian",
      value:"custodian",
      address: "globaleaks-custodian1@mailinator.com",
      idp_id: "PRKPTR88H01L219U",
    },
    {
      name: "Admin2",
      value:"admin",
      address: "globaleaks-admin2@mailinator.com",
      idp_id: "PRKPTR88H01L219U",
    },
    {
      name: "Analyst",
      value:"analyst",
      address: "globaleaks-analyst1@mailinator.com",
      idp_id: "PRKPTR88H01L219U",
    },
    {
      name: "Resp_Accreditation",
      value:"accreditor",
      address: "globaleaks-analyst1@mailinator.com",
      idp_id: "PRKPTR88H01L219U",
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
      cy.get('input[name="idp_id"]').clear().type(user.idp_id);
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
      cy.get("#edit_user").click();
      cy.get('input[name="can_mask_information"]').click();
      cy.get('input[name="can_redact_information"]').click();
      cy.get('input[name="can_grant_access_to_reports"]').click();
      cy.get('input[name="can_transfer_access_to_reports"]').click();
      cy.get('input[name="can_reopen_reports"]').click();
      cy.get('input[name="can_delete_submission"]').click();
      cy.get('input[name="can_edit_general_settings"]').click();
      cy.get('input[name="can_download_infected"]').click();
      cy.get("#save_user").click();
    });
  });

  it("should configure users' passwords", () => {
    cy.login_admin();
    cy.visit("/#/admin/users");

    cy.get(".userList").its("length").then(userListLength => {
      const numberOfUsers = Math.min(userListLength, 8);
      for (let i = 1; i < numberOfUsers; i++) {
        cy.get(".userList").eq(i).within(() => {
          if (Cypress.$("#edit_user").length > 0) {
            cy.get("#edit_user").should('be.visible', { timeout: 10000 }).click();
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
