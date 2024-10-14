import {TriggeredByOption, Attrs} from "@app/models/app/shared-public-model";

interface Option {
  id: string;
  order: number;
  block_submission: boolean;
  score_points: number;
  score_type: string;
  trigger_receiver: string[];
  hint1: string;
  hint2: string;
  label: string;
}

export interface Step {
  id: string;
  instance: string;
  editable: boolean;
  type: string;
  template_id: string;
  template_override_id: string;
  step_id: string;
  fieldgroup_id: string;
  multi_entry: boolean;
  required: boolean;
  preview: boolean;
  statistical: boolean;
  attrs: Attrs;
  x: number;
  y: number;
  width: number;
  questionnaire_id: string;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption[];
  options: Option[];
  children: Step[];
  label: string;
  description: string;
  hint: string;
  placeholder: string;
}

export class questionnaireResolverModel {
  id: string;
  editable: boolean;
  name: string;
  key: string;
  steps: Step[];
}