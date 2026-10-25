import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

export function requireSupabase() {
  if (!supabase) {
    throw new Error('Supabase Authentication is not configured for this deployment.');
  }
  return supabase;
}

export function supabaseErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    if (error.message.toLowerCase().includes('email not confirmed')) {
      return 'Verify your email using the link Supabase sent before signing in.';
    }
    return error.message;
  }
  return 'Supabase Authentication failed.';
}
