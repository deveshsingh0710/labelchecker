export interface BoundingBoxNormalized {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  image_width: number;
  image_height: number;
  normalized: BoundingBoxNormalized;
}

export interface ExtractedField {
  field_name: string;
  value: string | null;
  raw_text: string | null;
  confidence: number;
  found: boolean;
  bounding_box: BoundingBox | null;
  details: Record<string, any>;
}

export interface EvaluationItem {
  rule_id: string;
  field: string;
  title: string;
  status: 'PASS' | 'FAIL' | 'NEEDS_REVIEW';
  severity: 'critical' | 'major' | 'minor';
  weight: number;
  legal_reference: string;
  explanation: string;
  remediation: string;
  extracted_value: string | null;
  ocr_confidence: number;
  bounding_box: BoundingBox | null;
}

export interface VerificationResult {
  id: string;
  filename: string;
  raw_image_url: string;
  preprocessed_image_url: string;
  ocr_summary: {
    raw_text: string;
    average_confidence: number;
    total_lines: number;
    total_words: number;
  };
  overall_score: number;
  compliance_status: 'COMPLIANT' | 'PARTIALLY_COMPLIANT' | 'NON_COMPLIANT';
  total_passed: number;
  total_failed: number;
  total_needs_review: number;
  extracted_fields: Record<string, ExtractedField>;
  evaluation_results: EvaluationItem[];
  pdf_report_url: string | null;
  created_at?: string;
  error_message?: string;
}

export interface PreprocessingData {
  file_id: string;
  filename: string;
  raw_image_url: string;
  preprocessed_image_url: string;
  deskew_angle: number;
  original_dimensions: [number, number];
  preprocessed_dimensions: [number, number];
  metadata: Record<string, any>;
}

export interface SampleLabel {
  id: string;
  title: string;
  description: string;
  filename: string;
  image_url: string;
  expected_status: string;
}
