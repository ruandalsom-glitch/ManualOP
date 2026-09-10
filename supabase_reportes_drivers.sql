-- ============================================================
-- TABELA SUPABASE: reportes (Estrutura idêntica à planilha Google)
-- Colunas da planilha: protocolo | nome_driver | motivo | empresa | telefone | resposta_final | data_ultima_mensagem
-- Execute este script no SQL Editor do seu painel do Supabase
-- ============================================================

-- 1. Recriar a tabela 'reportes' com a estrutura exata da sua planilha
DROP TABLE IF EXISTS public.reportes CASCADE;

CREATE TABLE public.reportes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    protocolo TEXT,
    nome_driver TEXT,
    motivo TEXT,
    empresa TEXT,
    telefone TEXT,
    resposta_final TEXT,
    data_ultima_mensagem TEXT
);

-- 2. Habilitar Row Level Security (RLS)
ALTER TABLE public.reportes ENABLE ROW LEVEL SECURITY;

-- 3. Criar Políticas de Acesso RLS
DROP POLICY IF EXISTS "Permitir leitura publica de reportes" ON public.reportes;
CREATE POLICY "Permitir leitura publica de reportes" ON public.reportes 
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Permitir insercao e delecao de reportes" ON public.reportes;
CREATE POLICY "Permitir insercao e delecao de reportes" ON public.reportes 
    FOR ALL USING (true);

-- 4. Dados de exemplo alinhados às colunas reais para testes
INSERT INTO public.reportes (protocolo, nome_driver, motivo, empresa, telefone, resposta_final, data_ultima_mensagem) 
VALUES
('#REP-101', 'Carlos Eduardo da Silva', 'Problemas Cadastrais / Liberação', 'GO Sumarezinho', '(19) 99123-4567', 'APROVADO', '10/09/2026 14:20'),
('#REP-102', 'Mariana Souza Oliveira', 'Contestação de Promoções', 'GO Campinas', '(19) 99234-5678', 'EM ANÁLISE', '10/09/2026 11:45'),
('#REP-103', 'Roberto Alves Santos', 'Contestação de Garantido FE', 'GO Hortolândia', '(19) 99345-6789', 'PENDENTE', '09/09/2026 18:30'),
('#REP-104', 'Lucas Gabriel Pereira', 'Dúvidas Gerais', 'GO Americana', '(19) 99456-7890', 'REPROVADO', '08/09/2026 09:15');
