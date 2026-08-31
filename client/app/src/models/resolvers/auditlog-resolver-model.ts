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
  internaltip_id?: string;
  // The fingerprints an entry carries of the content it deleted
  hash_sha256?: string;
  hash_sha512?: string;
}