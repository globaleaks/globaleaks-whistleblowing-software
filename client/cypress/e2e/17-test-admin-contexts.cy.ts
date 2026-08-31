describe("admin configure, add, and delete channels", () => {
  it("should configure an existing channel", () => {
    cy.visit("/");
    cy.login_admin();

    cy.visit("#/admin/channels");

    cy.get("#context-0").within(() => {
      cy.get("[data-action='edit']").click();

      // the identifier of the channel, introduced by this version
      cy.takeScreenshot("admin/channel_slug_detail", '.form-group:has(#context-slug-input)');

      // A channel names user profiles, not users: the recipients of the suite hold a profile
      const add_receiver = (name: string) => {
        cy.get(".selection-list").then(($list) => {
          // the names are compared whole: "Profile1" is a piece of
          // "Profile10", and a substring would find one in the other
          const present = $list.find("li > span:last-child").toArray()
            .some((item) => item.textContent.trim() === name);

          if (present) {
            return;
          }

          cy.get(".add-receiver-btn").click();
          cy.get('ng-select[name="selected.value"]').click();
          cy.get('ng-select[name="selected.value"]').contains(name).click();
        });
      };

      add_receiver("Profile1");
      add_receiver("Profile2");

      // Declared available to the users of the site: it lets a recipient enter a report on it
      cy.get("#context-internally-available").then(($i) => {
        if (!$i.is(":checked")) {
          cy.wrap($i).click();
        }
      });

      cy.get("#advance_context").click();
      cy.get("[data-action='save']").click();
    });
  });

  it("should add new channels", () => {
    cy.visit("/");
    cy.login_admin();

    cy.visit("#/admin/channels");
    const add_context = (context_name: string) => {
      // asserted on the response, not on the rendering
      cy.intercept("POST", "/api/admin/contexts").as(`addContext-${context_name}`);
      cy.get(".show-add-context-btn").click();
      cy.get("[name='new_context.name']").type(context_name);
      cy.get("#add-btn").click();
      cy.wait(`@addContext-${context_name}`).its("response.statusCode").should("be.within", 200, 299);
      cy.contains("form[name='editContext']", context_name).should("be.visible");
    };

    add_context("Topic A");
    add_context("Topic B");
    add_context("Topic C");
  });

  it("should delete existing channels", () => {
    cy.visit("/");
    cy.login_admin();

    cy.visit("#/admin/channels");
    cy.get("[data-action='delete']").last().click();
    cy.get("#modal-action-ok").click();
    cy.get(".modal [type='password']").type(Cypress.env("user_password"));
    cy.get(".modal .btn-primary").click();

    cy.contains("form[name='editContext']", "Default").should("exist");

    cy.logout();
  });

  it("should add/remove new status and sub-status in the admin section", () => {
    cy.login_admin();

    cy.visit("/#/admin/casemanagement");
    cy.get(".config-section").should("be.visible");
    cy.get(".show-add-user-btn").click();
    cy.get(".addSubmissionStatus").should("be.visible");
    cy.get('input[name="name"]').type("Test");
    cy.get("#add-btn").click();
    cy.get("#status-closed").click();
    cy.get("#add-sub-status").click();
    cy.get('input[name="label"]').type("closed 1");
    cy.get("#add-submission-sub-status").click();
    cy.get("#add-sub-status").click();
    cy.get('input[name="label"]').type("closed 2");
    cy.get("#add-submission-sub-status").click();
    cy.get(".substatus [data-action='edit']").last().click();
    cy.get('input[name="substatus.label"]').clear();
    cy.get('input[name="substatus.label"]').type('Test Label').should('have.value', 'Test Label');
    cy.get('select[name="substatus.tip_timetolive_option"]').select(1);
    cy.get('input[name="substatus.tip_timetolive"]').clear();
    const inputValue = 10;
    cy.get('input[name="substatus.tip_timetolive"]').type(inputValue.toString()).should('have.value', inputValue.toString());
    cy.get(".substatus [data-action='save']").first().click();
    cy.get(".substatus [data-action='delete']").first().click();
    cy.get("#modal-action-ok").click();
    cy.get(".substatus [data-action='delete']").first().click();
    cy.get("#modal-action-ok").click();
    cy.get(".submissionStatus [data-action='delete']").last().click();
    cy.get("#modal-action-ok").click();
   
    cy.get(".show-add-user-btn").click();
    cy.get(".addSubmissionStatus").should("be.visible");
    cy.get('input[name="name"]').type("Partial");
    cy.get("#add-btn").click();
    cy.get(".config-section").contains("Partial").click();
    cy.get("#add-sub-status").click();
    cy.get('input[name="label"]').type("closed");
    cy.get("#add-submission-sub-status").click();

    cy.logout();
  });
});
