-- ============================================================
-- TABELA SUPABASE: reportes (Acompanhamento de Aprovação de Drivers)
-- Execute este script no SQL Editor do seu painel do Supabase
-- ============================================================

-- 1. Criar a tabela 'reportes' caso ela não exista
CREATE TABLE IF NOT EXISTS public.reportes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    driver_name TEXT NOT NULL,
    cpf TEXT,
    telefone TEXT,
    praca TEXT DEFAULT 'Geral',
    status TEXT NOT NULL DEFAULT 'EM ANÁLISE', -- Status aceitos: 'APROVADO', 'EM ANÁLISE', 'PENDENTE', 'REPROVADO'
    observacao TEXT,
    solicitante TEXT,
    tipo_solicitacao TEXT DEFAULT 'Cadastro de Driver'
);

-- 2. Habilitar Row Level Security (RLS)
ALTER TABLE public.reportes ENABLE ROW LEVEL SECURITY;

-- 3. Criar Políticas de Acesso (RLS)
-- Permitir leitura pública (para os usuários do site consultarem o status)
DROP POLICY IF EXISTS "Permitir leitura publica de reportes" ON public.reportes;
CREATE POLICY "Permitir leitura publica de reportes" ON public.reportes 
    FOR SELECT USING (true);

-- Permitir inserção e atualização pública/autenticada
DROP POLICY IF EXISTS "Permitir insercao e atualizacao de reportes" ON public.reportes;
CREATE POLICY "Permitir insercao e atualizacao de reportes" ON public.reportes 
    FOR ALL USING (true);

-- 4. Inserir dados de exemplo para testes de aprovação de drivers
INSERT INTO public.reportes (driver_name, cpf, telefone, praca, status, observacao, solicitante, tipo_solicitacao) 
VALUES
('Carlos Eduardo da Silva', '123.456.789-00', '(19) 99123-4567', 'Campinas', 'APROVADO', 'Cadastro liberado e ativo no aplicativo.', 'Equipe Cadastro', 'Aprovação Direta'),
('Mariana Souza Oliveira', '234.567.890-11', '(19) 99234-5678', 'Sumaré', 'EM ANÁLISE', 'CNH e Comprovante de Residência em validação.', 'Jira Bot', 'Análise Documental'),
('Roberto Alves Santos', '345.678.901-22', '(19) 99345-6789', 'Hortolândia', 'PENDENTE', 'Falta enviar foto da CNH aberta com EAR.', 'Suporte Operacional', 'Pendência de Documento'),
('Lucas Gabriel Pereira', '456.789.012-33', '(19) 99456-7890', 'Americana', 'REPROVADO', 'Documentação com divergência no nome do titular.', 'Equipe Cadastro', 'Reprovado');

-- 5. Atualizar automaticamente a coluna updated_at ao modificar registros
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_reportes_updated_at ON public.reportes;
CREATE TRIGGER update_reportes_updated_at
    BEFORE UPDATE ON public.reportes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
