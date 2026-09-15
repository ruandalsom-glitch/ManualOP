-- ============================================================
-- SQL Migration: Adicionar Coluna 'setor' na tabela 'reportes_colaboradores'
-- Execute este comando no SQL Editor do seu painel do Supabase
-- ============================================================

ALTER TABLE public.reportes_colaboradores 
ADD COLUMN IF NOT EXISTS setor TEXT DEFAULT 'Geral';
