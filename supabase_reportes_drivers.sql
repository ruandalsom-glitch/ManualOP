-- ============================================================
-- TABELA SUPABASE: reportes (Estrutura atualizada com 9 colunas)
-- Colunas da planilha: 
-- protocolo | nome_driver | cpf | motivo | empresa | telefone | resposta_final | mensagem_resposta | data_ultima_mensagem
-- Execute este script no SQL Editor do seu painel do Supabase
-- ============================================================

-- 1. Recriar a tabela 'reportes' com as 9 colunas da sua planilha
DROP TABLE IF EXISTS public.reportes CASCADE;

CREATE TABLE public.reportes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    protocolo TEXT,
    nome_driver TEXT,
    cpf TEXT,
    motivo TEXT,
    empresa TEXT,
    telefone TEXT,
    resposta_final TEXT,
    mensagem_resposta TEXT,
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

-- 4. Dados de exemplo com as 9 colunas e os status oficiais
INSERT INTO public.reportes (protocolo, nome_driver, cpf, motivo, empresa, telefone, resposta_final, mensagem_resposta, data_ultima_mensagem) 
VALUES
('4402125', 'Erick dos Santos Ribeiro', '213.515.737-64', 'Entrada Franquia', 'Recreio', '(21) 92197-9821', 'FALTA_DOCUMENTO', 'Aguardando foto legível da CNH com EAR.', '10/09/2026 14:20'),
('4664691', 'Matheus Manoel dos Santos', '208.204.337-13', 'Entrada Franquia', 'Recreio', '(21) 92199-3878', 'Aprovado_concluido', 'Driver liberado e ativo no aplicativo.', '10/09/2026 11:45'),
('4695386', 'Jonas Francisco', '468.799.698-10', 'Entrada Franquia', 'Sumarezinho', '(11) 98791-0372', 'PENDENCIA', 'Pendente verificação de dados bancários.', '09/09/2026 18:30'),
('4914667', 'Marcos Vinicius Da Silva Dos Santos', '205.069.247-18', 'Entrada Franquia', 'Recreio', '(21) 92198-3972', 'Aprovado_concluido', 'Cadastro totalmente aprovado.', '08/09/2026 09:15');
