import {UserProfile} from "@app/models/resolvers/user-resolver-model";

export type PermissionKey = keyof UserProfile["permissions"];

export interface PermissionItem {
  key: PermissionKey;
  label: string;
  rootOnly?: boolean;
}

export interface PermissionGroup {
  role: string;
  permissions: PermissionItem[];
}

// The administrative areas, labelled by the section name already translated for
// the sidebar; can_manage_sites exists only on the root tenant
export const ADMIN_AREAS: PermissionItem[] = [
  {key: "can_manage_settings", label: "Settings"},
  {key: "can_manage_users", label: "Users"},
  {key: "can_manage_user_profiles", label: "Users' profiles"},
  {key: "can_manage_questionnaires", label: "Questionnaires"},
  {key: "can_manage_channels", label: "Channels"},
  {key: "can_manage_case_management", label: "Case management"},
  {key: "can_manage_notifications", label: "Notifications"},
  {key: "can_manage_network", label: "Network"},
  {key: "can_manage_sites", label: "Sites", rootOnly: true},
  {key: "can_manage_auditlog", label: "Audit log"},
  {key: "can_manage_support", label: "Support"}
];

// The keys of the administrative areas, the single source the code derives the
// set of administrative permissions from
export const ADMIN_PERMISSION_KEYS: PermissionKey[] = ADMIN_AREAS.map(area => area.key);

// The recipient permissions, labelled by the noun of what they control rather
// than a sentence
export const RECIPIENT_PERMISSIONS: PermissionItem[] = [
  {key: "can_mask_information", label: "Mask information"},
  {key: "can_redact_information", label: "Redact information"},
  {key: "can_delete_submission", label: "Delete reports"},
  {key: "can_change_status", label: "Change report status"},
  {key: "can_change_label", label: "Change report labels"},
  {key: "can_postpone_expiration", label: "Postpone expiration date"},
  {key: "can_send_communications", label: "Send communication to other organizations"},
  {key: "can_grant_access_to_reports", label: "Grant access to reports"},
  {key: "can_transfer_access_to_reports", label: "Transfer access to reports"}
];

// Composing the statistical templates is offered to the administrators as well
export const ANALYST_PERMISSIONS: PermissionItem[] = [
  {key: "can_configure_statistical_report_templates", label: "Templates"}
];

/**
 * Build the permission subsections to render for a profile, one per role it
 * holds. can_manage_settings is an administrative area; a non administrator
 * recipient can be delegated it and finds it among its own permissions.
 */
export function buildPermissionGroups(roles: string[], onRootTenant: boolean): PermissionGroup[] {
  const isAdmin = roles.includes("admin");
  const groups: PermissionGroup[] = [];

  if (isAdmin) {
    groups.push({
      role: "Admin",
      permissions: [...ADMIN_AREAS.filter(area => !area.rootOnly || onRootTenant), ...ANALYST_PERMISSIONS]
    });
  }

  if (roles.includes("receiver")) {
    const permissions = [...RECIPIENT_PERMISSIONS];
    if (!isAdmin) {
      permissions.push({key: "can_manage_settings", label: "Settings"});
    }
    groups.push({role: "Recipient", permissions});
  }

  if (roles.includes("analyst")) {
    groups.push({role: "Analyst", permissions: ANALYST_PERMISSIONS});
  }

  return groups;
}
