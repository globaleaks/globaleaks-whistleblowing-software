export class NewUser {
  id = "";
  username = "";
  role = "receiver";
  enabled = true;
  password_change_needed = true;
  idp_id = "";
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
  can_edit_general_settings = false;
  can_grant_access_to_reports = false;
  can_delete_submission = false;
  can_postpone_expiration = true;
  can_transfer_access_to_reports = false;
  can_reopen_reports = false;
  can_redact_information = false;
  can_mask_information = false;
  can_download_infected = false;
}