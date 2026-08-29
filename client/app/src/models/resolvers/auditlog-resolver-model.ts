export class auditlogResolverModel {
  date: string;
  type: string;
  severity: number;
  user_id?: string;
  username?: string;
  object_id?: string;
  data?: Data;
}

export class Data {
  status: string;
  substatus?: string;
}