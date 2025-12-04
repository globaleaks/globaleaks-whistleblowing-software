export class auditlogResolverModel {
  date: string;
  type: string;
  severity: number;
  user_id?: string;
  object_id?: string;
  data?: any;
}

export class Data {
  status: string;
  substatus?: string;
}