import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// 타입 정의
export interface KeywordRow {
  id: string;
  query: string;
  country: string;
  ad_limit: number;
  enabled: boolean;
  created_at: string;
}

export interface ImageHashRow {
  id: string;
  image_hash: string;
  permanent_url: string;
  created_at: string;
}
