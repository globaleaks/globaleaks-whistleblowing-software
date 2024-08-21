export interface Organization {
    oe_id: string;
    name: string;
}

export interface ReviewForm {
    form_id: string;
    name: string;
}

export interface FileItem {
    id: string,
    name: string;
    scanStatus: string;
    origin: string;
    uploadDate: string;
    size: string;
    infected: boolean;
    loading: boolean;
  }
  
export interface SentTipDetail {
    organization: string;
    date: string;
    fileSent: number;
    status: string;
    text: string;
    review_form: any;
  }
  