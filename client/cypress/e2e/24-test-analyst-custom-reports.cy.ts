describe("Analyst - Custom Report Templates", () => {
  const template1Name = `Test Report ${Date.now()}`;
  const template2Name = `Test Report 2 ${Date.now()}`;

  it("should create the first custom report template", function () {
    cy.login_analyst();
    cy.waitForUrl("/analyst/home");

    // Navigate to statistics page (which shows templates list)
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();

    // Click the "New" button to create a template
    cy.get('button').contains('New').click();

    // Verify the creation form is visible
    cy.get('#templateName').should('be.visible');

    // Enter template name
    cy.get('#templateName').type(template1Name);

    // Click Create button
    cy.get('button[type="submit"]').contains('Create').click();

    // Wait for template to be created and redirect
    cy.waitForPageIdle();

    // Verify we're on the statistics page in edit mode
    cy.url().should('include', '/analyst/statistics/view');
    cy.get('[data-cy="statistics_save_button"]').should('be.visible');

    cy.logout();
  });

  it("should create the second custom report template", function () {
    cy.login_analyst();

    // Navigate to statistics page (which shows templates list)
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();

    // Click the "New" button
    cy.get('button').contains('New').click();

    // Enter template name
    cy.get('#templateName').type(template2Name);

    // Click Create button
    cy.get('button[type="submit"]').contains('Create').click();

    // Wait for redirect
    cy.waitForPageIdle();

    // Verify we're on the statistics page
    cy.url().should('include', '/analyst/statistics/view');

    cy.logout();
  });

  it("should customize the first report by adding a number metric", function () {
    cy.login_analyst();

    // Navigate to statistics page (which shows templates list)
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();

    // Wait for templates list to be visible
    cy.get('#templatesList').should('be.visible');

    // Find and open the first custom template by finding the row containing the template name
    cy.get('#templatesList tbody tr').contains(template1Name).parents('tr').within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Enter edit mode
    cy.get('button').contains('Edit').click();
    cy.waitForPageIdle();

    // Verify add button is visible
    cy.get('.add-metric-card').should('be.visible');

    // Click add metric card
    cy.get('.add-metric-card').click();

    // Wait for modal to open
    cy.get('.modal').should('be.visible');

    // Select the first predefined metric
    cy.get('.modal .metric-option').first().click();

    // Wait for display types to load
    cy.wait(200);

    // Select "Number" display type using data-cy
    cy.get('[data-cy="display-type-number"]').should('be.visible').click();

    // Click Add button using ID
    cy.get('#modal-action-ok').click();

    // Wait for modal to close and metric to be added
    cy.waitForPageIdle();

    // Verify metric card was added
    cy.get('.metric-card').should('have.length.at.least', 1);

    // Save changes
    cy.get('button').contains('Save').click();
    cy.waitForPageIdle();

    cy.logout();
  });

  it("should add a pie chart metric to the first report", function () {
    cy.login_analyst();

    // Navigate to statistics page and open first custom template
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
    cy.get('#templatesList').should('be.visible');
    cy.get('#templatesList tbody tr').contains(template1Name).parents('tr').within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Enter edit mode
    cy.get('button').contains('Edit').click();
    cy.waitForPageIdle();

    // Click add metric card
    cy.get('.add-metric-card').click();

    // Wait for modal
    cy.get('.modal').should('be.visible');

    // Find and select a metric compatible with pie chart
    // Use index since metric names are translated
    cy.get('.modal .metric-option').eq(1).click();

    // Wait for display types to load
    cy.wait(200);

    // Select "Pie Chart" display type using data-cy
    cy.get('[data-cy="display-type-pie"]').should('be.visible').click();

    // Click Add button using ID
    cy.get('#modal-action-ok').click();

    // Wait for modal to close
    cy.waitForPageIdle();

    // Verify chart was added
    cy.get('.chart-card').should('have.length.at.least', 1);

    // Save changes
    cy.get('button').contains('Save').click();
    cy.waitForPageIdle();

    cy.logout();
  });

  it("should add a bar chart metric to the first report", function () {
    cy.login_analyst();

    // Navigate to statistics page and open first custom template
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
    cy.get('#templatesList').should('be.visible');
    cy.get('#templatesList tbody tr').contains(template1Name).parents('tr').within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Enter edit mode
    cy.get('button').contains('Edit').click();
    cy.waitForPageIdle();

    // Click add metric card
    cy.get('.add-metric-card').click();

    // Wait for modal
    cy.get('.modal').should('be.visible');

    // Try to find a metric compatible with bar charts
    // We need to try multiple metrics since some may have been added already
    let foundBarChart = false;
    
    cy.get('.modal .metric-option').then($options => {
      const tryMetric = (index) => {
        if (index >= $options.length) {
          // No more metrics to try, fail the test
          throw new Error('No metrics compatible with bar charts found');
        }
        
        cy.get('.modal .metric-option').eq(index).click();
        cy.wait(300);
        
        cy.get('body').then($body => {
          if ($body.find('[data-cy="display-type-bar"]').length > 0) {
            // Found a compatible metric, select bar chart
            cy.get('[data-cy="display-type-bar"]').click();
          } else {
            // Try next metric
            tryMetric(index + 1);
          }
        });
      };
      
      tryMetric(0);
    });

    // Click Add button using ID
    cy.get('#modal-action-ok').click();

    // Wait for modal to close
    cy.waitForPageIdle();

    // Verify chart was added
    cy.get('.chart-card').should('exist');

    // Save changes
    cy.get('button').contains('Save').click();
    cy.waitForPageIdle();

    cy.logout();
  });

  it("should add a percentage metric to the first report", function () {
    cy.login_analyst();

    // Navigate to statistics page and open first custom template
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
    cy.get('#templatesList').should('be.visible');
    cy.get('#templatesList tbody tr').contains(template1Name).parents('tr').within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Enter edit mode
    cy.get('button').contains('Edit').click();
    cy.waitForPageIdle();

    // Click add metric card
    cy.get('.add-metric-card').click();

    // Wait for modal
    cy.get('.modal').should('be.visible');

    // Select another predefined metric
    cy.get('.modal .metric-option').eq(2).click();

    // Wait for display types to load
    cy.wait(200);

    // Select "Percentage" display type using data-cy
    cy.get('[data-cy="display-type-percentage"]').should('be.visible').click();

    // Click Add button using ID
    cy.get('#modal-action-ok').click();

    // Wait for modal to close
    cy.waitForPageIdle();

    // Verify metric was added
    cy.get('.metric-card').should('have.length.at.least', 2);

    // Save changes
    cy.get('button').contains('Save').click();
    cy.waitForPageIdle();

    cy.logout();
  });

  it("should manage/edit a metric in the first report", function () {
    cy.login_analyst();

    // Navigate to statistics page and open first custom template
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
    cy.get('#templatesList').should('be.visible');
    cy.get('#templatesList tbody tr').contains(template1Name).parents('tr').within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Enter edit mode
    cy.get('button').contains('Edit').click();
    cy.waitForPageIdle();

    // Click the dropdown menu on the first metric card
    cy.get('.metric-card .dropdown button').first().click();

    // Click Manage option
    cy.get('.dropdown-menu').contains('Manage').click();

    // Wait for manage modal
    cy.get('.modal').should('be.visible');

    // Change display type (e.g., from Number to Percentage)
    cy.get('.modal .display-type').eq(1).click();

    // Click Apply button using ID
    cy.get('#modal-action-ok').click();

    // Wait for modal to close
    cy.waitForPageIdle();

    // Save changes
    cy.get('button').contains('Save').click();
    cy.waitForPageIdle();

    cy.logout();
  });

  it("should remove a metric from the first report", function () {
    cy.login_analyst();

    // Navigate to statistics page and open first custom template
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
    cy.get('#templatesList').should('be.visible');
    cy.get('#templatesList tbody tr').contains(template1Name).parents('tr').within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Enter edit mode
    cy.get('button').contains('Edit').click();
    cy.waitForPageIdle();

    // Get initial count of metrics
    cy.get('.metric-card').its('length').then((initialCount) => {
      // Click the dropdown menu on the first metric card
      cy.get('.metric-card .dropdown button').first().click();

      // Click Remove option
      cy.get('.dropdown-menu').contains('Remove').click();

      // Verify one metric was removed
      cy.get('.metric-card').should('have.length', initialCount - 1);

      // Save changes
      cy.get('button').contains('Save').click();
      cy.waitForPageIdle();
    });

    cy.logout();
  });

  it("should export the customized first report as PDF", function () {
    cy.login_analyst();

    // Navigate to statistics page and open first custom template
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
    cy.get('#templatesList').should('be.visible');
    cy.get('#templatesList tbody tr').contains(template1Name).parents('tr').within(() => {
      cy.get('.analytics-action-open').click();
    });
    cy.waitForPageIdle();

    // Ensure we're in view mode (not edit mode)
    cy.url().should('include', '/analyst/statistics/view');

    // Wait for all content to load
    cy.waitForPageIdle();

    // Click export button
    cy.get('[data-cy="statistics_export_button"]').click();

    // Wait for PDF generation
    cy.wait(3000);

    // Verify we're still on the statistics page
    cy.url().should('include', '/analyst/statistics/view');

    cy.logout();
  });

  it("should delete the created custom templates", function () {
    cy.login_analyst();

    // Navigate to statistics page
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
    cy.get('#templatesList').should('be.visible');

    // Delete first template
    cy.get('#templatesList tbody tr').contains(template1Name).parents('tr').within(() => {
      cy.get('.analytics-action-delete').click();
    });

    // Confirm deletion in modal using ID
    cy.get('.modal').should('be.visible');
    cy.get('#modal-action-ok').click();

    // Wait for deletion
    cy.waitForPageIdle();

    // Delete second template
    cy.get('#templatesList tbody tr').contains(template2Name).parents('tr').within(() => {
      cy.get('.analytics-action-delete').click();
    });

    // Confirm deletion in modal using ID
    cy.get('.modal').should('be.visible');
    cy.get('#modal-action-ok').click();

    // Wait for deletion
    cy.waitForPageIdle();

    // Verify templates are no longer in the list
    cy.get('#templatesList tbody').should('not.contain', template1Name);
    cy.get('#templatesList tbody').should('not.contain', template2Name);

    cy.logout();
  });
});

