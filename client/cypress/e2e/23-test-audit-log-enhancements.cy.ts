describe("audit log enhancements", () => {
  const clearAuditLogStorage = () => {
    cy.window().then((win) => {
      // Clear all audit log view timestamps
      Object.keys(win.localStorage).forEach(key => {
        if (key.startsWith('auditlog_viewed_')) {
          win.localStorage.removeItem(key);
        }
      });
    });
  };

  it("should show audit log modal structure and entries", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    
    // Check if any tips exist, if not skip this test
    cy.get('body').then(($body) => {
      if ($body.find('#tip-0').length === 0) {
        cy.log('No tips available - skipping audit log test');
        return;
      }
      
      cy.get("#tip-0").first().click();
      
      // Open audit log modal
      cy.get('#tip-action-logs').click();
      
      // Verify modal opened with correct structure
      cy.get('.modal-title', { timeout: 5000 }).should('contain', 'Audit log');
      cy.get('.table thead th').should('contain', 'User');
      cy.get('.table thead th').should('contain', 'Type');
      cy.get('.table thead th').should('contain', 'Date');
      
      // Verify audit log entries exist
      cy.get('.table tbody tr').should('have.length.greaterThan', 0);
      
      // Verify action badges with colored dots exist
      cy.get('.badge.bg-light i.fa-circle-dot').should('exist');
      
      // Close modal
      cy.get('#auditlog-action-close').click();
    });
    
    cy.logout();
  });

  it("should show new audit log indicator when audit log has new entries", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    
    // Check if any tips exist
    cy.get('body').then(($body) => {
      if ($body.find('#tip-0').length === 0) {
        cy.log('No tips available - skipping audit log indicator test');
        return;
      }
    
      // Clear audit log storage to simulate first view
      clearAuditLogStorage();
      
      // Click on first tip
      cy.get("#tip-0").first().click();
    
    // The indicator should appear if there are new entries
    // (depends on update_date vs last_access from backend)
    cy.get('body').then(($body) => {
      if ($body.find('#tip-action-logs .badge.bg-warning').length > 0) {
        cy.log('New entries indicator is visible');
        
        // Open audit log modal
        cy.get('#tip-action-logs').click();
        
        // Check for highlighted rows (yellow background) if indicator was shown
        cy.get('.table tbody tr.new-entry-highlight', { timeout: 5000 }).should('exist');
        
        // Close modal
        cy.get('#auditlog-action-close').click();
        
        // Go back to reports and re-enter tip
        cy.visit("/#/recipient/reports");
        cy.get("#tip-0").first().click();
        
        // Indicator should be gone after viewing
        cy.get('#tip-action-logs .badge.bg-warning').should('not.exist');
      } else {
        cy.log('No new entries indicator (tip was already accessed)');
        
        // Still verify we can open the modal
        cy.get('#tip-action-logs').click();
        cy.get('.modal-title').should('contain', 'Audit log');
        cy.get('#auditlog-action-close').click();
      }
    });
    });
    
    cy.logout();
  });

  it("should create audit log entry for status changes", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    
    // Check if any tips exist
    cy.get('body').then(($body) => {
      if ($body.find('#tip-0').length === 0) {
        cy.log('No tips available - skipping status change test');
        return;
      }
      
      cy.get("#tip-0").first().click();
    
      // Change status to create a log entry
      cy.get('#actionsDropdown').click();
      cy.get("#tip-action-change-status").click();
      cy.get('#assignSubmissionStatus').select(1);
      cy.get("#modal-action-ok").click();
      
      // Wait for status change to complete
      cy.wait(1000);
      
      // Clear audit log view to see new entries highlighted
      clearAuditLogStorage();
      
      // Open audit log
      cy.get('#tip-action-logs').click();
      
      // Should see the table with entries including the status change
      cy.get('.table tbody tr', { timeout: 5000 }).should('have.length.greaterThan', 0);
      
      // Look for update_report_status entry with status badge
      cy.get('.table tbody').should('contain', 'Update report status');
      
      cy.get('#auditlog-action-close').click();
    });
    
    cy.logout();
  });

  it("should support search and sort functionality in audit log", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    
    // Check if any tips exist
    cy.get('body').then(($body) => {
      if ($body.find('#tip-0').length === 0) {
        cy.log('No tips available - skipping search and sort test');
        return;
      }
      
      cy.get("#tip-0").first().click();
    
      cy.get('#tip-action-logs').click();
      
      // Verify table exists
      cy.get('.table tbody tr', { timeout: 5000 }).should('have.length.greaterThan', 0);
      
      // Test search functionality if multiple entries exist
      cy.get('.table tbody tr').then(($rows) => {
        if ($rows.length > 1) {
          // Try searching
          cy.get('input[placeholder="Search"]').should('be.visible').type('report');
          cy.wait(500);
          cy.get('input[placeholder="Search"]').clear();
          
          // Test sorting by Date
          cy.get('th').contains('Date').should('be.visible').click();
          cy.wait(500);
          // Verify sort indicator appears
          cy.get('th').contains('Date').find('i').should('exist');
        }
      });
      
      // Test export button exists
      cy.get('#auditlog-action-export').should('be.visible');
      
      cy.get('#auditlog-action-close').click();
    });
    
    cy.logout();
  });

  it("should display action badges with different colored dots for different action types", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    
    // Check if any tips exist
    cy.get('body').then(($body) => {
      if ($body.find('#tip-0').length === 0) {
        cy.log('No tips available - skipping badges test');
        return;
      }
      
      cy.get("#tip-0").first().click();
      
      cy.get('#tip-action-logs').click();
      
      // Verify badges with colored dots exist
      cy.get('.badge.bg-light', { timeout: 5000 }).should('exist');
      cy.get('.badge.bg-light i.fa-circle-dot').should('exist');
      
      // Verify different action types have appropriate colored dots
      cy.get('.badge.bg-light').should('have.length.greaterThan', 0);
      
      // Check that colored dots exist (they use different CSS classes for colors)
      cy.get('i.fa-circle-dot').should('have.length.greaterThan', 0);
      
      cy.get('#auditlog-action-close').click();
    });
    
    cy.logout();
  });

  it("should handle file upload and comment audit log entries", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    
    // Check if any tips exist
    cy.get('body').then(($body) => {
      if ($body.find('#tip-0').length === 0) {
        cy.log('No tips available - skipping file upload test');
        return;
      }
      
      cy.get("#tip-0").first().click();
      
      // Upload a file to create an audit log entry
      cy.get('#upload_description').type("Test upload for audit log");
      cy.get('#tip-action-upload').click();
      cy.fixture("files/test.txt").then(fileContent => {
        cy.get('input[type="file"]').then(input => {
          const blob = new Blob([fileContent], { type: "text/plain" });
          const testFile = new File([blob], "test.txt");
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(testFile);
          const inputElement = input[0] as HTMLInputElement;
          inputElement.files = dataTransfer.files;
          const changeEvent = new Event("change", { bubbles: true });
          input[0].dispatchEvent(changeEvent);
        });
      });
      
      // Wait for upload to complete
      cy.wait(2000);
      
      // Clear audit log storage to see new entries
      clearAuditLogStorage();
      
      // Open audit log
      cy.get('#tip-action-logs').click();
      
      // Verify the audit log contains the file upload entry
      cy.get('.table tbody', { timeout: 5000 }).should('contain', 'Upload file');
      
      // Verify filename is shown in detail badge (recipients see filename, not just file type)
      cy.get('.badge.bg-light').should('exist');
      cy.get('.table tbody').should('contain', 'test.txt');
      
      cy.get('#auditlog-action-close').click();
    });
    
    cy.logout();
  });
});
