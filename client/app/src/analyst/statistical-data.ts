export interface StatisticalRequestModel {
    pg_size: number;
    pg_num: number;
    is_oe: boolean;
    date_from: string;
    date_to: string;
}

export interface ReportEntry {
    id: string;
    label: string;
    value: string | number | null;
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