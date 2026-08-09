/**
 * The entities an administrative page offers to choose from, served by
 * /api/admin/selectables to every administrator: the names, and the traits the
 * choice is made on. The areas they belong to are read through their own APIs,
 * each gated on the permission of that area.
 */
export interface SelectableUser {
  id: string;
  name: string;
  role: string;
  encryption: boolean;
  escrow: boolean;
}

export interface SelectableEntry {
  id: string;
  name: string;
}

export interface Selectables {
  users: SelectableUser[];
  contexts: SelectableEntry[];
  questionnaires: SelectableEntry[];
}
