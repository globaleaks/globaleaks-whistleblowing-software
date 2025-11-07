import {Field} from "@app/models/resolvers/field-template-model";
import {Option} from "@app/models/app/shared-public-model";

export interface ParsedFields {
  fields: Field[];
  fields_by_id: Record<string, Field>;
  options_by_id: Record<string, Option>;
}