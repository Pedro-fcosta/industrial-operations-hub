CREATE TABLE IF NOT EXISTS posicoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cr TEXT NOT NULL,
    posicao TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    local_atual TEXT NOT NULL,
    responsavel TEXT NOT NULL,
    observacao TEXT,
    data_cadastro TEXT NOT NULL,
    ultima_movimentacao TEXT
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cr TEXT NOT NULL,
    posicao TEXT NOT NULL,
    origem TEXT NOT NULL,
    destino TEXT NOT NULL,
    responsavel TEXT NOT NULL,
    observacao TEXT,
    data_hora TEXT NOT NULL
);