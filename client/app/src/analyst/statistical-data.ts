export interface StatisticalRequestModel {
    is_eo: boolean;
    date_from: string;
    date_to: string;
}
export interface ReportEntry {
    id: string;
    label: string;
    value: string | number | null;
}
export interface ResultsRow {
    [key: string]: string | number | null;
}

export type Results = ReportEntry[][];
export interface Summary {
    [key: string]: {
        [key: string]: number;
    };
}
export interface StatisticalResponseModel {
    results: Results;
    summary: Summary;
}