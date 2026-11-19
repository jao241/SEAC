import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID, uuid4

from app.conhecimento import SERVICOS, campo

DB = os.getenv("DATABASE_PATH", "/data/sqlite/simplifica.db")


def conexao():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def iniciar():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    with closing(conexao()) as db, db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS cidadaos (
            codigo TEXT PRIMARY KEY, nome TEXT NOT NULL, identificador TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS solicitacoes (
            protocolo TEXT PRIMARY KEY, operacao TEXT NOT NULL UNIQUE,
            cidadao TEXT NOT NULL REFERENCES cidadaos(codigo),
            servico TEXT NOT NULL, local TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Recebida',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        """)


def cadastrar(nome, identificador):
    nome = campo(nome, "o nome")
    identificador = campo(identificador, "o identificador", 60).casefold()
    with closing(conexao()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        existente = db.execute("SELECT codigo, nome FROM cidadaos WHERE identificador=?", (identificador,)).fetchone()
        if existente:
            return {"codigo": existente["codigo"], "nome": existente["nome"], "existente": True}
        codigo = "CID-" + uuid4().hex[:12].upper()
        db.execute("INSERT INTO cidadaos VALUES (?, ?, ?)", (codigo, nome, identificador))
        return {"codigo": codigo, "nome": nome, "existente": False}


def registrar(cidadao, servico, local, operacao):
    cidadao = cidadao.strip().upper()
    local = campo(local, "o local")
    try:
        operacao = str(UUID(operacao))
    except ValueError:
        raise ValueError("Identificador de operação inválido.")
    if servico not in SERVICOS:
        raise ValueError("Serviço fictício inexistente.")
    with closing(conexao()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        anterior = db.execute("SELECT * FROM solicitacoes WHERE operacao=?", (operacao,)).fetchone()
        if anterior:
            if (anterior["cidadao"], anterior["servico"], anterior["local"]) != (cidadao, servico, local):
                raise ValueError("Esta confirmação pertence a outra solicitação.")
            return resumo(anterior)
        if not db.execute("SELECT 1 FROM cidadaos WHERE codigo=?", (cidadao,)).fetchone():
            raise ValueError("Cadastro não encontrado.")
        protocolo = "DEMO-" + uuid4().hex[:12].upper()
        db.execute("INSERT INTO solicitacoes(protocolo,operacao,cidadao,servico,local) VALUES(?,?,?,?,?)",
                   (protocolo, operacao, cidadao, servico, local))
        return resumo(db.execute("SELECT * FROM solicitacoes WHERE protocolo=?", (protocolo,)).fetchone())


def consultar(protocolo):
    protocolo = protocolo.strip().upper()
    if not re.fullmatch(r"DEMO-[A-F0-9]{12}", protocolo):
        raise ValueError("Informe um protocolo no formato DEMO- seguido de 12 caracteres hexadecimais.")
    with closing(conexao()) as db:
        registro = db.execute("SELECT * FROM solicitacoes WHERE protocolo=?", (protocolo,)).fetchone()
    if not registro:
        raise ValueError("Protocolo não encontrado.")
    return resumo(registro)


def resumo(registro):
    return {"protocolo": registro["protocolo"], "servico": SERVICOS[registro["servico"]]["nome"],
            "local": registro["local"], "estado": registro["estado"], "criado_em": registro["criado_em"]}
