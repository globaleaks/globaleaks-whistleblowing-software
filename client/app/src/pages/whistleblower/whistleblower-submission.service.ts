import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class WhistleblowerSubmissionService {
  
  checkForInvalidFields(scope:any) {
    let enabled_counter = 0;
    for (let counter = 0; counter <= scope.navigation; counter++) {
      scope.validate[counter] = true;
      if (scope.questionnaire.steps[counter].enabled) {
        if (scope.stepForms.get(enabled_counter)?.invalid) {
          scope.navigation = counter;
          return false;
        }
	enabled_counter++;
      }
    }
    return true;
  }

  decrementStep(scope:any) {
    if (!scope.hasPreviousStep()) {
      return;
    }

    for (let i = scope.navigation - 1; i >= scope.firstStepIndex(); i--) {
      if (i === -1 || scope.fieldUtilitiesService.isFieldTriggered(null, scope.questionnaire.steps[i], scope.answers, scope.score)) {
        scope.navigation = i;
        scope.utilsService.scrollToTop();
        return;
      }
    }
  }

  incrementStep(scope:any) {
    if (!scope.hasNextStep()) {
      return;
    }

    if (!scope.runValidation()) {
      scope.utilsService.scrollToTop();
      return;
    }

    for (let i = scope.navigation + 1; i <= scope.lastStepIndex(); i++) {
      if (scope.fieldUtilitiesService.isFieldTriggered(null, scope.questionnaire.steps[i], scope.answers, scope.score)) {
        scope.navigation = i;
        scope.utilsService.scrollToTop();
        return;
      }
    }
  }
}
