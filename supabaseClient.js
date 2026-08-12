// Configuração do Supabase
const supabaseUrl = 'https://wpuyanodymsjzsqzbmfy.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndwdXlhbm9keW1zanpzcXpibWZ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY1NTA1NzQsImV4cCI6MjEwMjEyNjU3NH0.iKaC2aOd6lKhxMPyRXWQ02Eu6Eesdc_rYckYr_fp02o';

// O objeto "supabase" global é fornecido pelo CDN do supabase-js incluído no HTML
const supabaseClient = supabase.createClient(supabaseUrl, supabaseKey);

