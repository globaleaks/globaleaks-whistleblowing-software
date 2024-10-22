import { Component, OnInit } from "@angular/core";
import { NgForm } from "@angular/forms";
import { NgbDateStruct } from "@ng-bootstrap/ng-bootstrap";
import { ReportEntry, Results, StatisticalRequestModel, StatisticalResponseModel, Summary } from "@app/analyst/statistical-data";
import { HttpService } from "@app/shared/services/http.service";

@Component({
    selector: "src-reports",
    templateUrl: "./reports.component.html"
})
export class ReportsComponent implements OnInit {
    today = new Date();
    maxDate: NgbDateStruct;
    input_start_date: NgbDateStruct;
    input_end_date: NgbDateStruct;

    reportType: string = '';    
    
    fixedHeaders: string[] = [
        "internal_tip_id", "internal_tip_status",
        "internal_tip_creation_date", "internal_tip_update_date",
        "internal_tip_expiration_date", "internal_tip_read_receip",
        "internal_tip_file_count", "internal_tip_comment_count",
        "internal_tip_receiver_count"
    ];
    dinamicHeaders: string[] = [];
    tableHeaders: string[] = [];
    tableRows: string[][] = [];

    isSearchInitiated: boolean = false;

    allResults: Results = [];
    currentPage: number = 0;
    pageSize: number = 3;

    charts: any[] = [];
    summary: Summary = {};
    summaryKeys: { id: string, label: string }[] = [];
    
    constructor(private httpService: HttpService) {}

    ngOnInit(): void {
        this.today = new Date();

        this.maxDate = {
            year: this.today.getFullYear(),
            month: this.today.getMonth() + 1,
            day: this.today.getDate()
        };
        this.clearDateRange();
    }

    clearDateRange(): void {
        console.log("Clearing date range");
        const lastWeek = new Date(this.today);
        lastWeek.setDate(this.today.getDate() - 7);
        
        this.input_end_date = {
            year: this.today.getFullYear(),
            month: this.today.getMonth() + 1,
            day: this.today.getDate()
        };
        
        this.input_start_date = {
            year: lastWeek.getFullYear(),
            month: lastWeek.getMonth() + 1,
            day: lastWeek.getDate()
        };

        if(this.charts.length > 0) {
            this.charts = [];
        }
        this.isSearchInitiated = false;
    }

    onDateChange(): void {
        if (this.input_end_date && this.input_start_date) {
            const start = new Date(this.input_start_date.year, this.input_start_date.month - 1, this.input_start_date.day);
            const end = new Date(this.input_end_date.year, this.input_end_date.month - 1, this.input_end_date.day);

            if (end < start) {
                this.input_end_date = this.input_start_date;
            }
        }
    }

    formatDate(date: NgbDateStruct): string {
        if (!date) {
            return '';
        }
        const year = date.year;
        const month = date.month.toString().padStart(2, '0');
        const day = date.day.toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    searchReports(form: NgForm): void {
        if (form.valid) {
            this.isSearchInitiated = true;
            console.log("Form data:", {
                reportType: this.reportType,
                startDate: this.input_start_date,
                endDate: this.input_end_date
            });
            
            const dateFrom = this.formatDate(this.input_start_date);
            const dateTo = this.formatDate(this.input_end_date);

            const bodyReq: StatisticalRequestModel = {
                pg_size: 3,
                pg_num: 0,
                is_oe: this.reportType === 'tipsOE',
                date_from: dateFrom,
                date_to: dateTo
            };

            console.log("Request body:", bodyReq);

            this.httpService.getStatisticalData(bodyReq).subscribe({
                next: (res) => {
                    console.log("Response:", res);

                    // TODO: to be removed only for testing
                    res = this.mockResponse;
                    // END TODO: to be removed only for testing

                    this.processResponse(res);
                },
                error: (err) => {
                    console.error("Error:", err);
                }
            });
        } else {
            console.log("Il form non è valido.");
        }
    }

    private processResponse(res: StatisticalResponseModel): void {
        if (res && res.results && res.results.length > 0) {
            this.allResults = res.results;

            this.populateTableHeaders(this.allResults);
            this.populateTableRows(this.allResults);

            this.summary = res.summary;
            this.summaryKeys = Object.keys(this.summary).map((key) => {
                const entry = this.allResults[0].find((entry: ReportEntry) => entry.id === key);
                const label = entry ? entry.label : key;
                return { id: key, label: label };
            });

            this.currentPage = 0;
            this.updatePagination();

            console.log("Intestazioni della tabella:", this.tableHeaders);
            console.log("Righe della tabella:", this.tableRows);
        } else {
            this.tableHeaders = [];
            this.tableRows = [];
            console.log("Nessun risultato trovato.");
        }
    }

    updatePagination(): void {
        const startIndex = this.currentPage * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const currentPageData = this.allResults.slice(startIndex, endIndex);
      
        this.populateTableHeaders(currentPageData);
        this.populateTableRows(currentPageData);
    }

    changePage(newPage: number): void {
        if (newPage >= 0 && newPage < this.totalPages) {
            this.currentPage = newPage;
            this.updatePagination();
        }
    }

    get totalPages(): number {
        return Math.ceil(this.allResults.length / this.pageSize);
    }

    private populateTableHeaders(results: ReportEntry[][]): void {
        const dynamicHeadersSet = new Set<string>();
      
        results.forEach((reportArray: ReportEntry[]) => {
            reportArray.forEach((entry: ReportEntry) => {
                if (entry.id !== 'internal_tip_last_access' && !this.fixedHeaders.includes(entry.id)) {
                    dynamicHeadersSet.add(entry.label);
                }
            });
        });

        this.dinamicHeaders = Array.from(dynamicHeadersSet);
      
        this.tableHeaders = [...this.fixedHeaders, ...this.dinamicHeaders];
    }

    private populateTableRows(results: ReportEntry[][]): void {
        this.tableRows = results.map((reportArray: ReportEntry[]) => {
            const rowMap = new Map<string, string>();
            let lastAccess = '';
            let updateDate = '';

            reportArray.forEach((entry: ReportEntry) => {
                if (entry.id === 'internal_tip_last_access') {
                    lastAccess = String(entry.value);
                } else if (entry.id === 'internal_tip_update_date') {
                    updateDate = String(entry.value);
                    rowMap.set(entry.label, updateDate);
                } else {
                    rowMap.set(entry.label, String(entry.value));
            }
            });

            rowMap.set('internal_tip_read_receip', lastAccess >= updateDate ? '✔' : '✘');

            return this.tableHeaders.map((header: string) => {
                return rowMap.get(header) || '-';
            });
        });
    }

    addChart(): void {
        console.log("Aggiungi Grafico cliccato.");
        const initialColumn = this.summaryKeys.length > 0 ? this.summaryKeys[0] : null;
        this.charts.push({
            type: 'pie',
            columnId: initialColumn ? initialColumn.id : null,
            data: this.getChartData(initialColumn?.id ?? ''),
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    updateCharts(): void {
        this.charts.forEach((chart, index) => {
            console.log(`Aggiornamento grafico ${index + 1}`);
            console.log(`Tipo di grafico: ${chart.type}`);
            console.log(`ID colonna: ${chart.columnId}`);
            
            if (chart.columnId) {
                const newChartData = this.getChartData(chart.columnId);
                if (newChartData) {
                    chart.data = newChartData;
                    chart.options = {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            datalabels: {
                                formatter: (value: any, context: any) => {
                                    const dataset = context.chart.data.datasets[0];
                                    const total = dataset.data.reduce((acc: number, val: number) => acc + val, 0);
                                    const percentage = ((value / total) * 100).toFixed(2);
                                    return `${percentage}%`;
                                },
                                color: '#fff',
                                anchor: 'end',
                                align: 'start',
                                font: {
                                    weight: 'bold'
                                }
                            }
                        }
                    };
                } else {
                    console.warn(`Nessun dato valido trovato per la colonna: ${chart.columnId}`);
                }
            }
        });
    }

    removeChart(index: number): void {
        if (index >= 0 && index < this.charts.length) {
            this.charts.splice(index, 1);
        }
    }

    private getChartData(columnId: string): any {
        if (!columnId || !this.summary[columnId]) {
            console.warn("getChartData() - Column ID non valido o non trovato");
            return this.createEmptyChartData('Nessun dato');
        }
    
        const data = this.summary[columnId];
        if (!data) {
            console.warn(`getChartData() - No data found for column ID: ${columnId}`);
            return this.createEmptyChartData('Nessun dato');
        }
        
        const labels = Object.keys(data);
        const values = Object.values(data);
    
        return {
            labels: labels,
            datasets: [
                {
                    label: columnId,
                    data: values,
                    backgroundColor: this.getDefaultBackgroundColors()
                }
            ]
        };
    }
    
    private createEmptyChartData(label: string): any {
        return {
            labels: [],
            datasets: [
                {
                    label: label,
                    data: [],
                    backgroundColor: this.getDefaultBackgroundColors()
                }
            ]
        };
    }
    
    private getDefaultBackgroundColors(): string[] {
        return [
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 99, 132, 0.6)',
            'rgba(255, 205, 86, 0.6)',
            'rgba(75, 192, 192, 0.6)'
        ];
    }

    // TODO: to be removed only for testing
    mockResponse = {
        results: [
            [
                {
                    "id": "internal_tip_id",
                    "label": "internal_tip_id",
                    "value": "36a710f1-c4d5-4f6b-8ab5-c2b2ebcce9c2"
                },
                {
                    "id": "internal_tip_creation_date",
                    "label": "internal_tip_creation_date",
                    "value": "2024-10-17T12:44:30.751036Z"
                },
                {
                    "id": "internal_tip_last_access",
                    "label": "internal_tip_last_access",
                    "value": "2024-10-17T12:45:15.727464Z"
                },
                {
                    "id": "internal_tip_update_date",
                    "label": "internal_tip_update_date",
                    "value": "2024-10-17T12:44:30.751045Z"
                },
                {
                    "id": "internal_tip_expiration_date",
                    "label": "internal_tip_expiration_date",
                    "value": "2025-01-15T23:59:59Z"
                },
                {
                    "id": "internal_tip_status",
                    "label": "internal_tip_status",
                    "value": "new"
                },
                {
                    "id": "internal_tip_file_count",
                    "label": "internal_tip_file_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_comment_count",
                    "label": "internal_tip_comment_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_receiver_count",
                    "label": "internal_tip_receiver_count",
                    "value": 1
                },
                {
                    "id": "6f5d4713-9146-4473-9b50-35cf420d5496",
                    "label": "How are you involved in the reported facts?",
                    "value": "I'm a victim"
                },
                {
                    "id": "0f2c5077-90f3-4b0d-8346-21b5c3b8a627",
                    "label": "Do you have evidence to support your report?",
                    "value": "Yes"
                },
                {
                    "id": "8562fe35-2f5b-4329-a356-707331603280",
                    "label": "Have you reported the facts to other organizations and/or individuals?",
                    "value": "No"
                },
                {
                    "id": "8562fe35-ab5b-4329-a356-707331603280",
                    "label": "E' inventata?",
                    "value": "No"
                }
            ],
            [
                {
                    "id": "internal_tip_id",
                    "label": "internal_tip_id",
                    "value": "49deaba0-1e96-4bcc-8708-62abc55fecbd"
                },
                {
                    "id": "internal_tip_creation_date",
                    "label": "internal_tip_creation_date",
                    "value": "2024-10-17T12:46:18.250330Z"
                },
                {
                    "id": "internal_tip_last_access",
                    "label": "internal_tip_last_access",
                    "value": "2024-10-17T12:46:18.250346Z"
                },
                {
                    "id": "internal_tip_update_date",
                    "label": "internal_tip_update_date",
                    "value": "2024-10-18T09:05:22.827534Z"
                },
                {
                    "id": "internal_tip_expiration_date",
                    "label": "internal_tip_expiration_date",
                    "value": "2025-01-15T23:59:59Z"
                },
                {
                    "id": "internal_tip_status",
                    "label": "internal_tip_status",
                    "value": "opened"
                },
                {
                    "id": "internal_tip_file_count",
                    "label": "internal_tip_file_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_comment_count",
                    "label": "internal_tip_comment_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_receiver_count",
                    "label": "internal_tip_receiver_count",
                    "value": 1
                },
                {
                    "id": "6f5d4713-9146-4473-9b50-35cf420d5496",
                    "label": "How are you involved in the reported facts?",
                    "value": "I'm involved in the facts"
                },
                {
                    "id": "0f2c5077-90f3-4b0d-8346-21b5c3b8a627",
                    "label": "Do you have evidence to support your report?",
                    "value": "No"
                },
                {
                    "id": "8562fe35-2f5b-4329-a356-707331603280",
                    "label": "Have you reported the facts to other organizations and/or individuals?",
                    "value": "Yes"
                },
                {
                    "id": "8562fe35-ab5b-4329-a356-707331603280",
                    "label": "E' vera?",
                    "value": "No"
                }
            ],
            [
                {
                    "id": "internal_tip_id",
                    "label": "internal_tip_id",
                    "value": "36a710f1-c4d5-4f6b-8ab5-c2b2ebcce9c2"
                },
                {
                    "id": "internal_tip_creation_date",
                    "label": "internal_tip_creation_date",
                    "value": "2024-10-17T12:44:30.751036Z"
                },
                {
                    "id": "internal_tip_last_access",
                    "label": "internal_tip_last_access",
                    "value": "2024-10-17T12:45:15.727464Z"
                },
                {
                    "id": "internal_tip_update_date",
                    "label": "internal_tip_update_date",
                    "value": "2024-10-17T12:44:30.751045Z"
                },
                {
                    "id": "internal_tip_expiration_date",
                    "label": "internal_tip_expiration_date",
                    "value": "2025-01-15T23:59:59Z"
                },
                {
                    "id": "internal_tip_status",
                    "label": "internal_tip_status",
                    "value": "new"
                },
                {
                    "id": "internal_tip_file_count",
                    "label": "internal_tip_file_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_comment_count",
                    "label": "internal_tip_comment_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_receiver_count",
                    "label": "internal_tip_receiver_count",
                    "value": 1
                },
                {
                    "id": "6f5d4713-9146-4473-9b50-35cf420d5496",
                    "label": "How are you involved in the reported facts?",
                    "value": "I witnessed the facts in person"
                },
                {
                    "id": "0f2c5077-90f3-4b0d-8346-21b5c3b8a627",
                    "label": "Do you have evidence to support your report?",
                    "value": "No"
                },
                {
                    "id": "8562fe35-2f5b-4329-a356-707331603280",
                    "label": "Have you reported the facts to other organizations and/or individuals?",
                    "value": "Yes"
                },
                {
                    "id": "8562fe35-ab5b-4329-a356-707331603280",
                    "label": "E' vera?",
                    "value": "No"
                }
            ],
            [
                {
                    "id": "internal_tip_id",
                    "label": "internal_tip_id",
                    "value": "49deaba0-1e96-4bcc-8708-62abc55fecbd"
                },
                {
                    "id": "internal_tip_creation_date",
                    "label": "internal_tip_creation_date",
                    "value": "2024-10-17T12:46:18.250330Z"
                },
                {
                    "id": "internal_tip_last_access",
                    "label": "internal_tip_last_access",
                    "value": "2024-10-17T12:46:18.250346Z"
                },
                {
                    "id": "internal_tip_update_date",
                    "label": "internal_tip_update_date",
                    "value": "2024-10-18T09:05:22.827534Z"
                },
                {
                    "id": "internal_tip_expiration_date",
                    "label": "internal_tip_expiration_date",
                    "value": "2025-01-15T23:59:59Z"
                },
                {
                    "id": "internal_tip_status",
                    "label": "internal_tip_status",
                    "value": "opened"
                },
                {
                    "id": "internal_tip_file_count",
                    "label": "internal_tip_file_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_comment_count",
                    "label": "internal_tip_comment_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_receiver_count",
                    "label": "internal_tip_receiver_count",
                    "value": 1
                },
                {
                    "id": "6f5d4713-9146-4473-9b50-35cf420d5496",
                    "label": "How are you involved in the reported facts?",
                    "value": "I was personally told by a direct witness"
                },
                {
                    "id": "0f2c5077-90f3-4b0d-8346-21b5c3b8a627",
                    "label": "Do you have evidence to support your report?",
                    "value": "No"
                },
                {
                    "id": "8562fe35-2f5b-4329-a356-707331603280",
                    "label": "Have you reported the facts to other organizations and/or individuals?",
                    "value": "Yes"
                },
                {
                    "id": "8562fe35-ab5b-4329-a356-707331603280",
                    "label": "E' falsa?",
                    "value": "No"
                }
            ],
            [
                {
                    "id": "internal_tip_id",
                    "label": "internal_tip_id",
                    "value": "36a710f1-c4d5-4f6b-8ab5-c2b2ebcce9c2"
                },
                {
                    "id": "internal_tip_creation_date",
                    "label": "internal_tip_creation_date",
                    "value": "2024-10-17T12:44:30.751036Z"
                },
                {
                    "id": "internal_tip_last_access",
                    "label": "internal_tip_last_access",
                    "value": "2024-10-17T12:45:15.727464Z"
                },
                {
                    "id": "internal_tip_update_date",
                    "label": "internal_tip_update_date",
                    "value": "2024-10-17T12:44:30.751045Z"
                },
                {
                    "id": "internal_tip_expiration_date",
                    "label": "internal_tip_expiration_date",
                    "value": "2025-01-15T23:59:59Z"
                },
                {
                    "id": "internal_tip_status",
                    "label": "internal_tip_status",
                    "value": "new"
                },
                {
                    "id": "internal_tip_file_count",
                    "label": "internal_tip_file_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_comment_count",
                    "label": "internal_tip_comment_count",
                    "value": 0
                },
                {
                    "id": "internal_tip_receiver_count",
                    "label": "internal_tip_receiver_count",
                    "value": 1
                },
                {
                    "id": "6f5d4713-9146-4473-9b50-35cf420d5496",
                    "label": "How are you involved in the reported facts?",
                    "value": "It is a rumor I heard"
                },
                {
                    "id": "0f2c5077-90f3-4b0d-8346-21b5c3b8a627",
                    "label": "Do you have evidence to support your report?",
                    "value": "Yes"
                },
                {
                    "id": "8562fe35-2f5b-4329-a356-707331603280",
                    "label": "Have you reported the facts to other organizations and/or individuals?",
                    "value": "No"
                },
                {
                    "id": "8562fe35-ab5b-4329-a356-707331603280",
                    "label": "E' così così?",
                    "value": "No"
                }
            ]
        ],
        summary: {
            "status": {
                "new": 3,
                "opened": 2
            },
            "internal_tip_creation_date_years": {
                "2025": 1,
                "2024": 2
            },
            "internal_tip_creation_date_month": {
                "10": 1,
                "11": 2,
            },
            "file_count": {
                "0": 5
            },
            "comment_count": {
                "0": 5
            },
            "receiver_count": {
                "1": 5
            },
            "6f5d4713-9146-4473-9b50-35cf420d5496": {
                "I'm a victim": 1,
                "I'm involved in the facts": 1,
                "I witnessed the facts in person": 1,
                "I was personally told by a direct witness": 1,
                "It is a rumor I heard": 1
            },
            "0f2c5077-90f3-4b0d-8346-21b5c3b8a627": {
                "Yes": 2,
                "No": 3
            },
            "8562fe35-2f5b-4329-a356-707331603280": {
                "Yes": 3,
                "No": 2
            }
        }
    };
    // END TODO: to be removed only for testing

}