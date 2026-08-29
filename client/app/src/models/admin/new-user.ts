export class NewUserPermissions {
  can_postpone_expiration = true;
  can_delete_submission = false;
  can_grant_access_to_reports = false;
  can_manage_settings = false;
  can_manage_users = false;
  can_manage_user_profiles = false;
  can_manage_channels = false;
  can_manage_questionnaires = false;
  can_manage_case_management = false;
  can_manage_notifications = false;
  can_manage_network = false;
  can_manage_sites = false;
  can_manage_auditlog = false;
  can_manage_support = false;
  can_transfer_access_to_reports = false;
  can_forward_reports = false;
  can_change_status = true;
  can_change_label = true;
  can_mask_information = true;
  can_redact_information = false;
}

export class NewUserProfile {
  id = "";
  name = "";
  role = "";
  roles: string[] = [];
  contexts: string[] = [];
  permissions = new NewUserPermissions();
}

export class NewUser {
  id = "";
  username = "";
  role = "receiver";
  enabled = true;
  password_change_needed = true;
  name = "";
  description = "";
  public_name = "";
  mail_address = "";
  pgp_key_fingerprint = "";
  pgp_key_remove = false;
  pgp_key_public = "";
  pgp_key_expiration = "";
  language = "en";
  notification = true;
  forcefully_selected = false;
  profile_id = "";
  profile = new NewUserProfile();
  send_activation_link = true;
}
