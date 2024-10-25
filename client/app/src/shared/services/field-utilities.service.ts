import {Injectable} from "@angular/core";
import {Option, WhistleblowerIdentity} from "@app/models/app/shared-public-model";
import {ParsedFields} from "@app/models/component-model/parsedFields";
import {Answers} from "@app/models/reciever/reciever-tip-data";
import {Step} from "@app/models/resolvers/questionnaire-model";
import {Children} from "@app/models/whistleblower/wb-tip-data";
import {Constants} from "@app/shared/constants/constants";

@Injectable({
  providedIn: "root"
})
export class FieldUtilitiesService {


  parseQuestionnaire(questionnaire: any, parsedFields: ParsedFields) {
    questionnaire.steps.forEach((step: Step)=> {
      parsedFields = this.parseFields(step.children, parsedFields);
    });

    return parsedFields;
  }

  underscore(s: string) {
    return s.replace(new RegExp("-", "g"), "_");
  }

  fieldFormName(id: string) {
    return "fieldForm_" + this.underscore(id);
  }

  getValidator(field: any) {
    const validators: any = {
      "custom": field.attrs.regexp ? field.attrs.regexp.value : "",
      "none": "",
      "email": Constants.emailRegexp,
      "number": Constants.numberRegexp,
      "phonenumber": Constants.phoneNumberRegexp,
    };

    if (field.attrs.input_validation) {
      return validators[field.attrs.input_validation.value];
    } else {
      return "";
    }
  }

  getClass(field: any, row_length: number) {
    if (field.width !== 0) {
      return "col-md-" + field.width;
    }

    return "col-md-" + ((row_length > 12) ? 1 : (12 / row_length));
  }

  flatten_field = (id_map: any, field: any): void => {
    if (field.children.length === 0) {
      id_map[field.id] = field;
      return id_map;
    } else {
      id_map[field.id] = field;
      return field.children.reduce(this.flatten_field, id_map);
    }
  };

  build_field_id_map(questionnaire: any) {
    return questionnaire.steps.reduce((id_map: any, cur_step: any) => {
      return cur_step.children.reduce(this.flatten_field, id_map);
    }, {});
  }

  findField(answers_obj: any, field_id: any): any {
    let r;

    for (const key in answers_obj) {
      if (key === field_id) {
        return answers_obj[key][0];
      }

      if (Object.prototype.hasOwnProperty.call(answers_obj, key) && Array.isArray(answers_obj[key]) && answers_obj[key].length > 0) {
        r = this.findField(answers_obj[key][0], field_id);
        if (typeof r !== "undefined") {
          return r;
        }
      }
    }
    return r;
  }

  splitRows(fields: Children[]) {
    const rows: any = [];
    let y: number | null = null;

    fields.forEach(function (f: Children) {
      if (y !== f.y) {
        y = f.y;
        rows.push([]);
      }

      rows[rows.length - 1].push(f);
    });
    return rows;
  }

  calculateScore(scope: any, field: any, entry: any) {
    let i;

    if (["selectbox", "multichoice"].indexOf(field.type) > -1) {
      for (i = 0; i < field.options.length; i++) {
        if (entry["value"] === field.options[i].id) {
          if (field.options[i].score_type === "addition") {
            scope.points_to_sum += field.options[i].score_points;
          } else if (field.options[i].score_type === "multiplier") {
            scope.points_to_mul *= field.options[i].score_points;
          }
        }
      }
    } else if (field.type === "checkbox") {
      for (i = 0; i < field.options.length; i++) {
        if (entry[field.options[i].id]) {
          if (field.options[i].score_type === "addition") {
            scope.points_to_sum += field.options[i].score_points;
          } else if (field.options[i].score_type === "multiplier") {
            scope.points_to_mul *= field.options[i].score_points;
          }
        }
      }
    } else if (field.type === "fieldgroup") {
      field.children.forEach((field: any) => {
        entry[field.id]?.forEach((entry: any) => {
          this.calculateScore(scope, field, entry);
        });
      });

      return;
    }

    const score = scope.points_to_sum * scope.points_to_mul;
    if (scope.context) {
      if (score < scope.context.score_threshold_medium) {
        scope.score = 1;
      } else if (score < scope.context.score_threshold_high) {
        scope.score = 2;
      } else {
        scope.score = 3;
      }
    }
  }

  updateAnswers(scope: any, parent: any, list: any, answers: any) {
    let entry, option, i, j;

    list.forEach((field: any) => {
      if (this.isFieldTriggered(parent, field, scope.answers, scope.score)) {
        if (!(field.id in answers)) {
          answers[field.id] = [{}];
        }
      } else {
        if (field.id in answers) {
          answers[field.id] = [{}];
        }
      }

      if (field.id in answers) {
        for (i = 0; i < answers[field.id].length; i++) {
          this.updateAnswers(scope, field, field.children, answers[field.id][i]);
        }
      } else {
        this.updateAnswers(scope, field, field.children, {});
      }

      if (!field.enabled) {
        return;
      }

      if (scope.appDataService?.public.node.enable_scoring_system) {
        scope.answers[field.id]?.forEach((entry: any) => {
          this.calculateScore(scope, field, entry);
        })
      }

      for (i = 0; i < answers[field.id].length; i++) {
        entry = answers[field.id][i];

        if (["inputbox", "textarea"].indexOf(field.type) > -1) {
          entry.required_status = (field.required || field.attrs.min_len.value > 0) && !entry["value"];
        } else if (field.type === "checkbox") {
          if (!field.required) {
            entry.required_status = false;
          } else {
            entry.required_status = true;
            for (j = 0; j < field.options.length; j++) {
              if (entry[field.options[j].id]) {
                entry.required_status = false;
                break;
              }
            }
          }
        } else if (field.type === "fileupload") {
          entry.required_status = field.required && (!scope.uploads[field.id] || !scope.uploads[field.id].size);
        } else {
          entry.required_status = field.required && !entry["value"];
        }

        if (["checkbox", "selectbox", "multichoice"].indexOf(field.type) > -1) {
          for (j = 0; j < field.options.length; j++) {
            option = field.options[j];
            option.set = false;
            if (field.type === "checkbox") {
              if (entry[option.id]) {
                option.set = true;
              }
            } else {
              if (option.id === entry["value"]) {
                option.set = true;
              }
            }

            if (option.set) {
              if (option.block_submission) {
                scope.block_submission = true;
              }

              if (scope.submissionService && option.trigger_receiver.length) {
                scope.submissionService.override_receivers = scope.submissionService.override_receivers.concat(option.trigger_receiver);
              }
            }
          }
        }
      }
    });
  }

  onAnswersUpdate(scope: any) {
    scope.block_submission = false;
    scope.score = 0;
    scope.points_to_sum = 0;
    scope.points_to_mul = 1;

    if (!scope.questionnaire) {
      return;
    }

    if (scope.submissionService) {
      scope.submissionService.override_receivers = [];
    }

    scope.questionnaire.steps.forEach((step: any) => {
      step.enabled = this.isFieldTriggered(null, step, scope.answers, scope.score);
      this.updateAnswers(scope, step, step.children, scope.answers);
    });

    if (scope.context) {
      scope.submissionService.submission.score = scope.score;
      scope.submissionService.blocked = scope.block_submission;
    }
  }


  isFieldTriggered(parent: any, field: any, answers: Answers | WhistleblowerIdentity, score: number) {
    let count = 0;
    let i;

    field.enabled = false;

    if (parent !== null && !parent.enabled) {
      return false;
    }

    if (field.triggered_by_score > score) {
      return false;
    }

    if (!field.triggered_by_options || field.triggered_by_options.length === 0) {
      field.enabled = true;
      return true;
    }

    for (i = 0; i < field.triggered_by_options.length; i++) {
      const trigger = field.triggered_by_options[i];
      const answers_field = this.findField(answers, trigger.field);
      if (typeof answers_field === "undefined") {
        continue;
      }

      if (trigger.option === answers_field.value ||
        Object.prototype.hasOwnProperty.call(answers_field, trigger.option) && answers_field[trigger.option]) {
        if (trigger.sufficient) {
          field.enabled = true;
          return true;
        }

        count += 1;
      }
    }

    if (count === field.triggered_by_options.length) {
      field.enabled = true;
      return true;
    }

    return false;
  }

  parseFields(fields: any, parsedFields: any) {

    fields.forEach((field: any) =>{
      parsedFields = this.parseField(field, parsedFields);
    });

    return parsedFields;
  }

  parseField(field: any, parsedFields: ParsedFields) {
    if (!Object.keys(parsedFields).length) {
      parsedFields.fields = [];
      parsedFields.fields_by_id = {};
      parsedFields.options_by_id = {};
    }

    if (["checkbox", "selectbox", "multichoice"].indexOf(field.type) > -1) {
      parsedFields.fields_by_id[field.id] = field;
      parsedFields.fields.push(field);
      field.options.forEach(function (option: Option) {
        parsedFields.options_by_id[option.id] = option;
      });

    } else if (field.type === "fieldgroup") {
      field.children.forEach((childField: any) => {
        this.parseField(childField, parsedFields);
      });
    }

    return parsedFields;
  }
}
