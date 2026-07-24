import { axiosInstance } from "./api";
import type { ResultadoParPR } from "./api";

export interface MergeJobResult {
  success: boolean;
  total_files_processed: number;
  total_qna_extracted: number;
  total_qna_merged: number;
  json_output_filename?: string;
  txt_output_filename?: string;
  warnings: string[];
  qna_pairs: ResultadoParPR[];
}

export interface MergeService {
  consolidateFiles(
    inputFormat: "json" | "txt",
    files: File[]
  ): Promise<MergeJobResult>;
}

export class ProductionMergeService implements MergeService {
  async consolidateFiles(
    inputFormat: "json" | "txt",
    files: File[]
  ): Promise<MergeJobResult> {
    const formData = new FormData();
    formData.append("input_format", inputFormat);
    for (const file of files) {
      formData.append("files", file);
    }

    const response = await axiosInstance.post<MergeJobResult>(
      "/api/merger/consolidate",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  }
}

export const mergeService = new ProductionMergeService();
