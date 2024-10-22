export class SendTip {
  tip_id: string;
  tids: number[] = [];
  text: string;
  files: AttachmentFile[] = [];
  questionnaire_id: string;
}

export interface AttachmentFile {
  id: string;
  origin: string;
}


export interface ReviewForm {
    form_id: string;
    name: string;
}

export interface FileItem {
    id: string,
    name: string;
    status: string;
    origin: string;
    uploadDate: string;
    size: number;
    file?: File;
    description?: string;
    verification_date?: string | null;
    download_url?: string;
  }
  
export interface SentTipDetail {
    organization: string;
    date: string;
    fileSent: number;
    status: string;
    text: string;
    review_form: any;
  }
  