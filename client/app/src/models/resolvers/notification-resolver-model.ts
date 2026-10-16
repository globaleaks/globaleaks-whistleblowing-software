export class notificationSettingsResolverModel {
  enable_admin_notification_emails: boolean;
  enable_custodian_notification_emails: boolean;
  enable_receiver_notification_emails: boolean;
  enable_analyst_notification_emails: boolean;
  tip_expiration_threshold: number;
}

/**
 * One of the two servers the mails are sent through, with its variables named without the
 * prefix that tells them apart: the password is written and never read back, and the server says
 * only whether it holds one. Each server is turned on and off on its own; the secondary one also
 * says for which notifications it is used.
 */
export class smtpResolverModel {
  server: string;
  port: number;
  security: string;
  authentication: boolean;
  username: string;
  password = "";
  password_set: boolean;
  source_email: string;
  enabled: boolean;
  template_types: string[] = [];
}

export class notificationTemplatesResolverModel {
  account_activation_mail_template: string;
  account_activation_mail_title: string;
  account_recovery_key_instructions: string;
  activation_mail_template: string;
  activation_mail_title: string;
  admin_anomaly_activities: string;
  admin_anomaly_disk_high: string;
  admin_anomaly_disk_low: string;
  admin_anomaly_mail_template: string;
  admin_anomaly_mail_title: string;
  admin_pgp_alert_mail_template: string;
  admin_pgp_alert_mail_title: string;
  admin_signup_alert_mail_template: string;
  admin_signup_alert_mail_title: string;
  admin_test_mail_template: string;
  admin_test_mail_title: string;
  email_validation_mail_template: string;
  email_validation_mail_title: string;
  export_template: string;
  https_certificate_expiration_mail_template: string;
  https_certificate_expiration_mail_title: string;
  https_certificate_renewal_failure_mail_template: string;
  https_certificate_renewal_failure_mail_title: string;
  identity_access_authorized_mail_template: string;
  identity_access_authorized_mail_title: string;
  identity_access_denied_mail_template: string;
  identity_access_denied_mail_title: string;
  identity_access_request_mail_template: string;
  identity_access_request_mail_title: string;
  identity_provided_mail_template: string;
  identity_provided_mail_title: string;
  password_reset_validation_mail_template: string;
  password_reset_validation_mail_title: string;
  pgp_alert_mail_template: string;
  pgp_alert_mail_title: string;
  signup_mail_template: string;
  signup_mail_title: string;
  signup_invite_mail_template: string;
  signup_invite_mail_title: string;
  software_update_available_mail_template: string;
  software_update_available_mail_title: string;
  tip_access_mail_template: string;
  tip_access_mail_title: string;
  tip_expiration_summary_mail_template: string;
  tip_expiration_summary_mail_title: string;
  tip_mail_template: string;
  tip_mail_title: string;
  tip_update_mail_template: string;
  tip_update_mail_title: string;
  unread_tips_mail_template: string;
  unread_tips_mail_title: string;
  user_credentials: string;
  templates: string[];

  [key: string]: string | string[];
}
