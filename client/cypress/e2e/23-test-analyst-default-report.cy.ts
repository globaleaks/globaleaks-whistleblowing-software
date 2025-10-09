describe("Analyst - Default Report Statistics", () => {
  it("should login as analyst and view the default report template", function () {
    cy.login_analyst();
    cy.waitForUrl("/analyst/home");

    // Navigate to templates list
    cy.visit("/#/analyst/templates");
    cy.waitForPageIdle();

    // Verify templates table is visible
    cy.get('#templatesList').should('be.visible');

    // Find and open the default template (first row in the table)
    cy.get('#templatesList tbody tr').first().within(() => {
      cy.get('.analytics-action-open').click();
    });

    // Wait for statistics page to load
    cy.url().should('include', '/analyst/statistics/view');
    cy.waitForPageIdle();

    // Verify page header and content loaded
    cy.get('.analyst-statistics-container').should('be.visible');
    cy.get('h2').should('be.visible');

    // Verify metric cards are displayed
    cy.get('.metric-card').should('exist');

    // Verify filters section is visible
    cy.get('.filter-section').should('be.visible');

    cy.logout();
  });

  it("should apply date range filter and view updated statistics", function () {
    cy.login_analyst();

    // Navigate directly to templates and open first template
    cy.visit("/#/analyst/templates");
    cy.waitForPageIdle();
    cy.get('#templatesList tbody tr').first().within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Open date range filter
    cy.get('.filter-item').contains('Date Range').parent().within(() => {
      cy.get('button.filter-btn').click();
    });

    // Select date range (using the date picker that appears)
    cy.get('.filter-dropdown-calendar').should('be.visible');
    
    // Click the first visible, clickable date in the current month
    cy.get('.ngb-dp-day').not('.hidden').not('[aria-disabled="true"]').first().click({ force: true });
    
    // Click another visible date to complete the range
    cy.get('.ngb-dp-day').not('.hidden').not('[aria-disabled="true"]').eq(5).click({ force: true });

    // Wait for data to reload
    cy.waitForPageIdle();

    // Verify the filter is now active
    cy.get('.filter-btn.active').should('exist');

    cy.logout();
  });


  it("should clear all filters", function () {
    cy.login_analyst();

    // Navigate to statistics
    cy.visit("/#/analyst/templates");
    cy.waitForPageIdle();
    cy.get('#templatesList tbody tr').first().within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Apply a date range filter first
    cy.get('.filter-item').contains('Date Range').parent().within(() => {
      cy.get('button.filter-btn').click();
    });
    cy.get('.filter-dropdown-calendar').should('be.visible');
    cy.get('.ngb-dp-day').not('.hidden').not('[aria-disabled="true"]').first().click({ force: true });
    cy.get('.ngb-dp-day').not('.hidden').not('[aria-disabled="true"]').eq(5).click({ force: true });
    cy.waitForPageIdle();

    // Verify filter is active
    cy.get('.filter-btn.active').should('exist');

    // Clear all filters
    cy.get('button').contains('Clear All').click();
    cy.waitForPageIdle();

    // Verify no active filters
    cy.get('.filter-btn.active').should('not.exist');

    cy.logout();
  });

  it("should export the default report as PDF", function () {
    cy.login_analyst();

    // Navigate to statistics
    cy.visit("/#/analyst/templates");
    cy.waitForPageIdle();
    cy.get('#templatesList tbody tr').first().within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Wait for all content to load
    cy.get('.metric-card').should('exist');
    cy.waitForPageIdle();

    // Click export button
    cy.get('[data-cy="statistics_export_button"]').click();

    // Wait for PDF generation (the button will be temporarily disabled)
    cy.wait(3000);

    // Verify we're still on the statistics page
    cy.url().should('include', '/analyst/statistics/view');

    cy.logout();
  });

  it("should navigate back to templates list", function () {
    cy.login_analyst();

    // Navigate to statistics
    cy.visit("/#/analyst/templates");
    cy.waitForPageIdle();
    cy.get('#templatesList tbody tr').first().within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Click back button
    cy.get('.fa-arrow-left').parent().click();

    // Verify we're back at templates list
    cy.url().should('include', '/analyst/templates');
    cy.get('#templatesList').should('be.visible');

    cy.logout();
  });
});

