export interface Step {
  enabled: boolean;
  invalid: boolean;
  id: string;
  questionnaire_id: string;
  order: number;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption[];
  children: Children[];
  label: string;
  description: string;
}

export interface Children {
  id: string;
  instance: string;
  editable: boolean;
  type: string;
  template_id: string;
  template_override_id: string;
  step_id: string;
  fieldgroup_id: string;
  questionnaire_id: string;
  multi_entry: boolean;
  required: boolean;
  preview: boolean;
  statistical: boolean;
  attrs: Attrs;
  x: number;
  y: number;
  width: number;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption[];
  options: Option[];
  children: Children[];
  label: string;
  description: string;
  hint: string;
  placeholder: string;
  enabled: boolean;
}

export interface Attrs {
  input_validation: InputValidation;
  max_len: MaxLen;
  min_len: MinLen;
  min_time: LocalizedSetting;
  max_time: LocalizedSetting;
  regexp: Regexp;
  display_alphabetically: DisplayAlphabetically;
  text_shown_upon_negative_answer: LocalizedSetting;
  min_date: MinMaxDate;
  max_date: MinMaxDate;
  text: LocalizedSetting;
  checkbox_label: LocalizedSetting;
  attachment: BoolSetting;
  attachment_text: LocalizedSetting;
  attachment_url: LocalizedSetting;
  multimedia: BoolSetting;
  multimedia_type: UnicodeSetting;
  multimedia_url: UnicodeSetting;
}

export interface BoolSetting {
  type: string;
  value: boolean;
}

export interface UnicodeSetting {
  type: string;
  value: string;
}

export interface MinMaxDate {
  type: string;
  value: { year: number; month: number; day: number } | string;
}

export interface LocalizedSetting {
  type: string;
  value: string;
}

export interface InputValidation {
  name: string;
  type: string;
  value: string;
}

export interface MaxLen {
  name: string;
  type: string;
  value: string;
}

export interface MinLen {
  name: string;
  type: string;
  value: string;
}

export interface Regexp {
  name: string;
  type: string;
  value: string;
}

export interface DisplayAlphabetically {
  name: string;
  type: string;
  value: boolean;
}

export interface TriggeredByOption {
  field: string;
  option: string;
  sufficient: boolean;
}

export interface Option {
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

export interface Comment {
  id: string;
  creation_date: string;
  content: string;
  author_id: string;
  visibility: string;
  type: string;
  data: any;
  tids: number[];
  eo_name: string;
}

export interface WbFile {
  id: string;
  ifile_id: string;
  creation_date: string;
  name: string;
  size: number;
  type: string;
  reference_id: string;
  error: boolean;
  status: string;
  verification_date: string;
  is_scan_expired: boolean;
}

export interface RFile {
  id: string;
  creation_date: string;
  name: string;
  size: number;
  type: string;
  description: string;
  visibility: string;
  error: boolean;
  author: string;
  downloads: number;
  status: string;
  isLoading: boolean;
  verification_date: string | null;
}

export interface QuestionWhistleblowerIdentityName {
  required_status: boolean;
  value: string;
}

export interface QuestionWhistleblowerIdentitySurname {
  required_status: boolean;
  value: string;
}

export interface QuestionWhistleblowerIdentityAlternativeContactMethod {
  required_status: boolean;
  value: string;
}

export interface QuestionWhistleblowerIdentityOther {
  required_status: boolean;
  value: string;
}

export interface WhistleblowerIdentity {
  question_whistleblower_identity_name: QuestionWhistleblowerIdentityName[];
  question_whistleblower_identity_surname: QuestionWhistleblowerIdentitySurname[];
  question_whistleblower_identity_alternative_contact_method: QuestionWhistleblowerIdentityAlternativeContactMethod[];
  required_status: boolean;
  value: string;
  question_whistleblower_identity_other: QuestionWhistleblowerIdentityOther[];
}

export interface SubmissionStatus {
  id: string;
  order: number;
  substatuses: SubmissionStatus[];
  label: string;
  status?: string;
  substatus?: string;
}


export interface ForwardedFile {
  id: string;
  creation_date: string;
  name: string;
  size: number;
  type: string;
}
