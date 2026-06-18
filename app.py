from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3
from datetime import datetime
import os
import csv
import io
import zipfile


# =======================================================

app = Flask(__name__)
app.secret_key = 'hub_setor_torres'


# =========================
# CONFIGURAÇÕES GERAIS
# =========================

DATABASE = "database.db"
PASTA_EXPORTS_BI = r"C:\Pedro Costa\NUCLEP\HUB Torres\exports"


SETORES = [
    "Aguardando Logística",

    # Máquinas
    "XP12-T4",
    "HP12-T4 Sul",
    "HP12-T4 Norte",
    "HP16T6",
    "P83",
    "Terrablade",
    "Messer",

    # Processos
    "Recorte",
    "Ferramentaria",
    "Dobra",
    "Furo Pós Dobra",
    "Acabamento",
    "Dimensional",
    "Área de Embarque",
    "Expedição",
    "Outro"
]

MAQUINAS = [
    "XP12-T4",
    "HP12-T4 Sul",
    "HP12-T4 Norte",
    "HP16T6",
    "P83",
    "Terrablade",
    "Messer",
    "Tronmaq ED",
    "Tronmaq Anexo",
    "Serra Fita",
    "Furadeira Radial",
    "Outra"
]

TIPOS_MANUTENCAO = [
    "Corretiva",
    "Preventiva",
    "Preditiva",
    "Inspeção",
    "Lubrificação",
    "Ajuste",
    "Limpeza",
    "Troca de Ferramenta",
    "Outro"
]

STATUS_MANUTENCAO = [
    "Parada",
    "Em manutenção",
    "Concluída",
    "Aguardando peça",
    "Aguardando manutenção",
    "Cancelada"
]

MOTIVOS_ESPERA_MATERIAL = [
    "Material não localizado",
    "Material aguardando logística",
    "Material aguardando liberação",
    "Material aguardando corte",
    "Material aguardando dobra",
    "Material aguardando furo",
    "Material com divergência",
    "Material aguardando retrabalho",
    "Outro"
]

STATUS_ESPERA_MATERIAL = [
    "Esperando material",
    "Material recebido",
    "Cancelada"
]

TIPOS_MATERIAL = [
    "Cantoneira",
    "Chapa",
    "Viga U",
    "Barra redonda",
    "Tubo",
    "Outro"
]

QUALIDADES_MATERIAL = [
    "A36",
    "A572 GR50",
    "A572 GR60",
    "SAE 1020",
    "SAE 1045",
    "SAE 1080",
    "Outro"
]


# ==============================================================================

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def coluna_existe(tabela, coluna):
    conn = get_connection()
    colunas = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    conn.close()

    for c in colunas:
        if c["name"] == coluna:
            return True

    return False


def calcular_tempo_entre_datas(data_inicio_str, data_fim_str=None):
    formato = "%d/%m/%Y %H:%M:%S"

    if not data_inicio_str:
        return ""

    inicio = datetime.strptime(data_inicio_str, formato)

    if data_fim_str:
        fim = datetime.strptime(data_fim_str, formato)
    else:
        fim = datetime.now()

    diferenca = fim - inicio
    total_segundos = int(diferenca.total_seconds())

    if total_segundos < 0:
        total_segundos = 0

    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60

    return f"{horas}h {minutos}min"


def calcular_minutos_entre_datas(data_inicio_str, data_fim_str=None):
    formato = "%d/%m/%Y %H:%M:%S"

    if not data_inicio_str:
        return 0

    inicio = datetime.strptime(data_inicio_str, formato)

    if data_fim_str:
        fim = datetime.strptime(data_fim_str, formato)
    else:
        fim = datetime.now()

    diferenca = fim - inicio
    total_segundos = int(diferenca.total_seconds())

    if total_segundos < 0:
        total_segundos = 0

    return total_segundos // 60


def calcular_horas_desde_data(data_str):
    formato = "%d/%m/%Y %H:%M:%S"

    if not data_str:
        return ""

    try:
        data = datetime.strptime(data_str, formato)
        agora = datetime.now()
        diferenca = agora - data

        total_segundos = int(diferenca.total_seconds())

        if total_segundos < 0:
            return 0

        horas = total_segundos // 3600

        return horas

    except:
        return ""


def init_db():
    conn = get_connection()

    conn.execute("""
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
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            posicao_id INTEGER,
            cr TEXT NOT NULL,
            posicao TEXT NOT NULL,
            origem TEXT NOT NULL,
            destino TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            observacao TEXT,
            data_hora TEXT NOT NULL
        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS manutencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maquina TEXT NOT NULL,
            tipo_manutencao TEXT NOT NULL,
            descricao TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            status TEXT NOT NULL,
            observacao TEXT,
            data_registro TEXT NOT NULL
        )
    """)


    conn.execute("""
    CREATE TABLE IF NOT EXISTS esperas_material (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        maquina TEXT NOT NULL,
        responsavel_inicio TEXT NOT NULL,
        tipo_material TEXT NOT NULL,
        qualidade_material TEXT,
        medidas TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        cr_material TEXT,
        observacao_inicio TEXT,
        data_inicio TEXT NOT NULL,
        responsavel_fim TEXT,
        observacao_fim TEXT,
        data_fim TEXT,
        tempo_total TEXT,
        status TEXT NOT NULL
    )
""")
    
    conn.commit()
    conn.close()

    # Garante compatibilidade caso seu banco antigo não tenha posicao_id
    if not coluna_existe("movimentacoes", "posicao_id"):
        conn = get_connection()
        conn.execute("ALTER TABLE movimentacoes ADD COLUMN posicao_id INTEGER")
        conn.commit()
        conn.close()
    
    if not coluna_existe("manutencoes", "data_atualizacao"):
        conn = get_connection()
        conn.execute("ALTER TABLE manutencoes ADD COLUMN data_atualizacao TEXT")
        conn.commit()
        conn.close()
    
    if not coluna_existe("esperas_material", "qualidade_material"):
        conn = get_connection()
        conn.execute("ALTER TABLE esperas_material ADD COLUMN qualidade_material TEXT")
        conn.commit()
        conn.close()

    if not coluna_existe("esperas_material", "cr_material"):
        conn = get_connection()
        conn.execute("ALTER TABLE esperas_material ADD COLUMN cr_material TEXT")
        conn.commit()
        conn.close()


# =========================
# HUB PRINCIPAL
# =========================

@app.route('/')
def index():
    return render_template('index.html')


# =========================
# MÓDULO RASTREABILIDADE
# =========================

@app.route("/rastreabilidade")
def rastreabilidade():
    return render_template("rastreabilidade/index.html")


@app.route("/rastreabilidade/cadastrar", methods=["GET", "POST"])
def rastreabilidade_cadastrar():
    if request.method == "POST":
        cr = request.form["cr"].strip()
        posicao = request.form["posicao"].strip()
        quantidade = request.form["quantidade"].strip()
        local_atual = request.form["local_atual"].strip()
        responsavel = request.form["responsavel"].strip()
        observacao = request.form.get("observacao", "").strip()

        outro_local_inicial = request.form.get("outro_local_inicial", "").strip()

        if local_atual == "Outro" and outro_local_inicial:
            local_atual = f"Outro - {outro_local_inicial}"

        data_agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        conn = get_connection()
        conn.execute("""
            INSERT INTO posicoes
            (cr, posicao, quantidade, local_atual, responsavel, observacao, data_cadastro, ultima_movimentacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cr,
            posicao,
            quantidade,
            local_atual,
            responsavel,
            observacao,
            data_agora,
            data_agora
        ))

        conn.commit()
        conn.close()

        flash("Posição cadastrada com sucesso!")
        return redirect(url_for("rastreabilidade_cadastrar"))

    return render_template("rastreabilidade/cadastrar.html", setores=SETORES)


@app.route("/rastreabilidade/movimentar", methods=["GET", "POST"])
def rastreabilidade_movimentar():
    lotes_encontrados = []
    lote_selecionado = None

    if request.method == "POST":
        acao = request.form.get("acao")

        if acao == "buscar":
            cr = request.form["cr"].strip()
            posicao = request.form["posicao"].strip()

            conn = get_connection()
            lotes_encontrados = conn.execute("""
                SELECT 
                    id,
                    cr,
                    posicao,
                    quantidade,
                    local_atual,
                    ultima_movimentacao
                FROM posicoes
                WHERE cr = ? AND posicao = ?
                ORDER BY local_atual, quantidade
            """, (cr, posicao)).fetchall()
            conn.close()

            if len(lotes_encontrados) == 0:
                flash("Nenhuma posição encontrada para esse CR e Posição.")

            elif len(lotes_encontrados) == 1:
                lote_selecionado = lotes_encontrados[0]

            return render_template(
                "rastreabilidade/movimentar.html",
                setores=SETORES,
                lotes_encontrados=lotes_encontrados,
                lote_selecionado=lote_selecionado
            )

        elif acao == "selecionar_lote":
            posicao_id = request.form["posicao_id"]

            conn = get_connection()
            lote_selecionado = conn.execute("""
                SELECT 
                    id,
                    cr,
                    posicao,
                    quantidade,
                    local_atual,
                    ultima_movimentacao
                FROM posicoes
                WHERE id = ?
            """, (posicao_id,)).fetchone()
            conn.close()

            return render_template(
                "rastreabilidade/movimentar.html",
                setores=SETORES,
                lotes_encontrados=[],
                lote_selecionado=lote_selecionado
            )

        elif acao == "registrar":
            posicao_id = request.form["posicao_id"]
            destino = request.form["destino"].strip()
            responsavel = request.form["responsavel"].strip()
            observacao = request.form.get("observacao", "").strip()
            quantidade_movimentar = int(request.form["quantidade_movimentar"])

            outro_destino = request.form.get("outro_destino", "").strip()

            if destino == "Outro" and outro_destino:
                destino = outro_destino

            conn = get_connection()

            lote = conn.execute("""
                SELECT *
                FROM posicoes
                WHERE id = ?
            """, (posicao_id,)).fetchone()

            if lote is None:
                conn.close()
                flash("Lote não encontrado.")
                return redirect(url_for("rastreabilidade_movimentar"))

            quantidade_atual = int(lote["quantidade"])
            origem = lote["local_atual"]
            data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            if quantidade_movimentar <= 0:
                conn.close()
                flash("A quantidade movimentada precisa ser maior que zero.")
                return redirect(url_for("rastreabilidade_movimentar"))

            if quantidade_movimentar > quantidade_atual:
                conn.close()
                flash("A quantidade movimentada não pode ser maior que a quantidade do lote.")
                return redirect(url_for("rastreabilidade_movimentar"))

            # CASO 1: movimentação total do lote
            if quantidade_movimentar == quantidade_atual:
                conn.execute("""
                    UPDATE posicoes
                    SET local_atual = ?,
                        responsavel = ?,
                        observacao = ?,
                        ultima_movimentacao = ?
                    WHERE id = ?
                """, (
                    destino,
                    responsavel,
                    observacao,
                    data_hora,
                    posicao_id
                ))

                observacao_historico = observacao

            # CASO 2: movimentação parcial do lote
            else:
                quantidade_restante = quantidade_atual - quantidade_movimentar

                # Atualiza o lote original, reduzindo a quantidade e mantendo no local atual
                conn.execute("""
                    UPDATE posicoes
                    SET quantidade = ?,
                        ultima_movimentacao = ?
                    WHERE id = ?
                """, (
                    quantidade_restante,
                    data_hora,
                    posicao_id
                ))

                # Cria um novo lote com a quantidade movimentada no novo destino
                cursor = conn.execute("""
                    INSERT INTO posicoes
                    (cr, posicao, quantidade, local_atual, responsavel, observacao, data_cadastro, ultima_movimentacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lote["cr"],
                    lote["posicao"],
                    quantidade_movimentar,
                    destino,
                    responsavel,
                    observacao,
                    data_hora,
                    data_hora
                ))

                novo_posicao_id = cursor.lastrowid

                observacao_historico = (
                    f"Movimentação parcial de {quantidade_movimentar} peça(s). "
                    f"Lote original permaneceu com {quantidade_restante} peça(s) em {origem}. "
                    f"Novo lote criado com ID {novo_posicao_id}. "
                )

                if observacao:
                    observacao_historico += f"Observação: {observacao}"

            # Registra o histórico da movimentação
            conn.execute("""
                INSERT INTO movimentacoes
                (posicao_id, cr, posicao, origem, destino, responsavel, observacao, data_hora)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                posicao_id,
                lote["cr"],
                lote["posicao"],
                origem,
                destino,
                responsavel,
                observacao_historico,
                data_hora
            ))

            conn.commit()
            conn.close()

            flash("Movimentação registrada com sucesso!")
            return redirect(url_for("rastreabilidade_movimentar"))

    return render_template(
        "rastreabilidade/movimentar.html",
        setores=SETORES,
        lotes_encontrados=[],
        lote_selecionado=None
    )


@app.route("/rastreabilidade/consultar", methods=["GET", "POST"])
def rastreabilidade_consultar():
    resultados = []
    cr = ""
    posicao = ""

    if request.method == "POST":
        cr = request.form.get("cr", "").strip()
        posicao = request.form.get("posicao", "").strip()

        query = """
            SELECT *
            FROM posicoes
            WHERE 1 = 1
        """
        parametros = []

        if cr:
            query += " AND cr = ?"
            parametros.append(cr)

        if posicao:
            query += " AND posicao = ?"
            parametros.append(posicao)

        query += " ORDER BY cr, posicao, local_atual"

        conn = get_connection()
        resultados = conn.execute(query, parametros).fetchall()
        conn.close()

        if not resultados:
            flash("Nenhuma posição encontrada com os filtros informados.")

    return render_template(
        "rastreabilidade/consultar.html",
        resultados=resultados,
        cr=cr,
        posicao=posicao
    )


@app.route("/rastreabilidade/historico", methods=["GET", "POST"])
def rastreabilidade_historico():
    historicos = []
    cr = ""
    posicao = ""

    if request.method == "POST":
        cr = request.form.get("cr", "").strip()
        posicao = request.form.get("posicao", "").strip()
    else:
        cr = request.args.get("cr", "").strip()
        posicao = request.args.get("posicao", "").strip()

    if request.method == "POST" or cr or posicao:
        query = """
            SELECT *
            FROM movimentacoes
            WHERE 1 = 1
        """
        parametros = []

        if cr:
            query += " AND cr = ?"
            parametros.append(cr)

        if posicao:
            query += " AND posicao = ?"
            parametros.append(posicao)

        query += " ORDER BY id DESC"

        conn = get_connection()
        historicos = conn.execute(query, parametros).fetchall()
        conn.close()

        if not historicos:
            flash("Nenhum histórico encontrado com os filtros informados.")

    return render_template(
        "rastreabilidade/historico.html",
        historicos=historicos,
        cr=cr,
        posicao=posicao
    )


@app.route("/rastreabilidade/exportar-historico-csv")
def rastreabilidade_exportar_historico_csv():
    cr = request.args.get("cr", "").strip()
    posicao = request.args.get("posicao", "").strip()

    query = """
        SELECT 
            id,
            posicao_id,
            cr,
            posicao,
            origem,
            destino,
            responsavel,
            observacao,
            data_hora
        FROM movimentacoes
        WHERE 1 = 1
    """
    parametros = []

    if cr:
        query += " AND cr = ?"
        parametros.append(cr)

    if posicao:
        query += " AND posicao = ?"
        parametros.append(posicao)

    query += " ORDER BY id DESC"

    conn = get_connection()
    dados = conn.execute(query, parametros).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID Movimentação",
        "ID Lote",
        "CR",
        "Posição",
        "Origem",
        "Destino",
        "Responsável",
        "Observação",
        "Data/Hora"
    ])

    for linha in dados:
        writer.writerow([
            linha["id"],
            linha["posicao_id"],
            linha["cr"],
            linha["posicao"],
            linha["origem"],
            linha["destino"],
            linha["responsavel"],
            linha["observacao"],
            linha["data_hora"]
        ])

    csv_final = "\ufeff" + output.getvalue()

    if cr and posicao:
        nome_arquivo = f"historico_{cr}_{posicao}.csv"
    elif cr:
        nome_arquivo = f"historico_CR_{cr}.csv"
    elif posicao:
        nome_arquivo = f"historico_posicao_{posicao}.csv"
    else:
        nome_arquivo = "historico_geral_rastreabilidade.csv"

    nome_arquivo = (
        nome_arquivo
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "_")
    )

    return Response(
        csv_final,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={nome_arquivo}"
        }
    )


@app.route("/rastreabilidade/relatorio")
def rastreabilidade_relatorio():
    conn = get_connection()
    posicoes = conn.execute("""
        SELECT *
        FROM posicoes
        ORDER BY ultima_movimentacao DESC
    """).fetchall()
    conn.close()

    return render_template(
        "rastreabilidade/relatorio.html",
        posicoes=posicoes
    )


@app.route("/rastreabilidade/exportar-csv")
def rastreabilidade_exportar_csv():
    conn = get_connection()
    dados = conn.execute("""
        SELECT 
            id,
            cr,
            posicao,
            quantidade,
            local_atual,
            responsavel,
            observacao,
            data_cadastro,
            ultima_movimentacao
        FROM posicoes
        ORDER BY ultima_movimentacao DESC
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID",
        "CR",
        "Posição",
        "Quantidade",
        "Local Atual",
        "Responsável",
        "Observação",
        "Data Cadastro",
        "Última Movimentação"
    ])

    for linha in dados:
        writer.writerow([
            linha["id"],
            linha["cr"],
            linha["posicao"],
            linha["quantidade"],
            linha["local_atual"],
            linha["responsavel"],
            linha["observacao"],
            linha["data_cadastro"],
            linha["ultima_movimentacao"]
        ])

    csv_final = "\ufeff" + output.getvalue()

    return Response(
        csv_final,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=relatorio_rastreabilidade.csv"
        }
    )



# =========================
# MÓDULO DE MANUTENÇÃO
# =========================

@app.route('/manutencao')
def manutencao():
    return render_template('manutencao/index.html')


@app.route("/manutencao/registrar", methods=["GET", "POST"])
def manutencao_registrar():
    if request.method == "POST":
        maquina = request.form["maquina"].strip()
        tipo_manutencao = request.form["tipo_manutencao"].strip()
        descricao = request.form["descricao"].strip()
        responsavel = request.form["responsavel"].strip()
        status = request.form["status"].strip()
        observacao = request.form.get("observacao", "").strip()

        outra_maquina = request.form.get("outra_maquina", "").strip()
        outro_tipo = request.form.get("outro_tipo", "").strip()

        if maquina == "Outra" and outra_maquina:
            maquina = f"Outra - {outra_maquina}"

        if tipo_manutencao == "Outro" and outro_tipo:
            tipo_manutencao = f"Outro - {outro_tipo}"

        data_registro = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        conn = get_connection()
        conn.execute("""
            INSERT INTO manutencoes
            (maquina, tipo_manutencao, descricao, responsavel, status, observacao, data_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            maquina,
            tipo_manutencao,
            descricao,
            responsavel,
            status,
            observacao,
            data_registro
        ))
        conn.commit()
        conn.close()

        flash("Manutenção registrada com sucesso!")
        return redirect(url_for("manutencao_registrar"))

    return render_template(
        "manutencao/registrar.html",
        maquinas=MAQUINAS,
        tipos_manutencao=TIPOS_MANUTENCAO,
        status_manutencao=STATUS_MANUTENCAO
    )


@app.route("/manutencao/consultar", methods=["GET", "POST"])
def manutencao_consultar():
    conn = get_connection()
    registros = conn.execute("""
        SELECT *
        FROM manutencoes
        WHERE status NOT IN ('Concluída', 'Cancelada')
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    maquina = ""
    status = ""
    tipo_manutencao = ""

    if request.method == "POST":
        maquina = request.form.get("maquina", "").strip()
        status = request.form.get("status", "").strip()
        tipo_manutencao = request.form.get("tipo_manutencao", "").strip()

        query = """
            SELECT *
            FROM manutencoes
            WHERE 1 = 1
        """
        parametros = []

        if maquina:
            query += " AND maquina = ?"
            parametros.append(maquina)

        if status:
            query += " AND status = ?"
            parametros.append(status)

        if tipo_manutencao:
            query += " AND tipo_manutencao = ?"
            parametros.append(tipo_manutencao)

        query += " ORDER BY id DESC"

        conn = get_connection()
        registros = conn.execute(query, parametros).fetchall()
        conn.close()

        if not registros:
            flash("Nenhuma manutenção encontrada com os filtros informados.")

    return render_template(
        "manutencao/consultar.html",
        registros=registros,
        maquinas=MAQUINAS,
        tipos_manutencao=TIPOS_MANUTENCAO,
        status_manutencao=STATUS_MANUTENCAO,
        maquina=maquina,
        status=status,
        tipo_manutencao=tipo_manutencao
    )


@app.route("/manutencao/atualizar-status", methods=["POST"])
def manutencao_atualizar_status():
    manutencao_id = request.form["manutencao_id"]
    novo_status = request.form["novo_status"].strip()
    observacao_atualizacao = request.form.get("observacao_atualizacao", "").strip()
    data_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    conn = get_connection()

    registro = conn.execute("""
        SELECT observacao
        FROM manutencoes
        WHERE id = ?
    """, (manutencao_id,)).fetchone()

    if registro is None:
        conn.close()
        flash("Registro de manutenção não encontrado.")
        return redirect(url_for("manutencao_consultar"))

    observacao_antiga = registro["observacao"] or ""

    if observacao_atualizacao:
        nova_observacao = (
            observacao_antiga
            + f"\n[{data_atualizacao}] Atualização: {observacao_atualizacao}"
        ).strip()
    else:
        nova_observacao = observacao_antiga

    conn.execute("""
        UPDATE manutencoes
        SET status = ?, observacao = ?, data_atualizacao = ?
        WHERE id = ?
    """, (
        novo_status,
        nova_observacao,
        data_atualizacao,
        manutencao_id
    ))

    conn.commit()
    conn.close()

    flash("Status da manutenção atualizado com sucesso!")
    return redirect(url_for("manutencao_consultar"))


@app.route("/manutencao/historico", methods=["GET", "POST"])
def manutencao_historico():
    historicos = []
    maquina = ""

    if request.method == "POST":
        maquina = request.form["maquina"].strip()
    else:
        maquina = request.args.get("maquina", "").strip()

    if maquina:
        conn = get_connection()
        historicos = conn.execute("""
            SELECT *
            FROM manutencoes
            WHERE maquina = ?
            ORDER BY id DESC
        """, (maquina,)).fetchall()
        conn.close()

        if not historicos:
            flash("Nenhum histórico encontrado para essa máquina.")

    return render_template(
        "manutencao/historico.html",
        historicos=historicos,
        maquinas=MAQUINAS,
        maquina=maquina
    )


@app.route("/manutencao/relatorio")
def manutencao_relatorio():
    conn = get_connection()
    registros = conn.execute("""
        SELECT *
        FROM manutencoes
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    return render_template(
        "manutencao/relatorio.html",
        registros=registros
    )


@app.route("/manutencao/exportar-csv")
def manutencao_exportar_csv():
    conn = get_connection()
    dados = conn.execute("""
        SELECT *
        FROM manutencoes
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID",
        "Máquina",
        "Tipo de Manutenção",
        "Descrição",
        "Responsável",
        "Status",
        "Observação",
        "Data Registro",
        "Última Atualização"
    ])

    for linha in dados:
        writer.writerow([
            linha["id"],
            linha["maquina"],
            linha["tipo_manutencao"],
            linha["descricao"],
            linha["responsavel"],
            linha["status"],
            linha["observacao"],
            linha["data_registro"],
            linha["data_atualizacao"]
        ])

    csv_final = "\ufeff" + output.getvalue()

    return Response(
        csv_final,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=relatorio_manutencao.csv"
        }
    )


@app.route("/manutencao/exportar-historico-csv")
def manutencao_exportar_historico_csv():
    maquina = request.args.get("maquina", "").strip()

    if not maquina:
        flash("Informe a máquina para exportar o histórico.")
        return redirect(url_for("manutencao_historico"))

    conn = get_connection()
    dados = conn.execute("""
        SELECT *
        FROM manutencoes
        WHERE maquina = ?
        ORDER BY id DESC
    """, (maquina,)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID",
        "Máquina",
        "Tipo de Manutenção",
        "Descrição",
        "Responsável",
        "Status",
        "Observação",
        "Data Registro",
        "Última Atualização"
    ])

    for linha in dados:
        writer.writerow([
            linha["id"],
            linha["maquina"],
            linha["tipo_manutencao"],
            linha["descricao"],
            linha["responsavel"],
            linha["status"],
            linha["observacao"],
            linha["data_registro"],
            linha["data_atualizacao"]
        ])

    csv_final = "\ufeff" + output.getvalue()

    nome_arquivo = f"historico_manutencao_{maquina}.csv"
    nome_arquivo = nome_arquivo.replace("/", "-").replace("\\", "-").replace(" ", "_")

    return Response(
        csv_final,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={nome_arquivo}"
        }
    )


# =========================
# MÓDULO DE ESPERA DE MATERIAL
# =========================

@app.route('/espera_material')
def espera_material():
    return render_template('espera_material/index.html')

@app.route("/espera-material/registrar", methods=["GET", "POST"])
def espera_material_registrar():
    if request.method == "POST":
        maquina = request.form["maquina"].strip()
        responsavel_inicio = request.form["responsavel_inicio"].strip()

        tipo_material = request.form["tipo_material"].strip()
        outro_tipo_material = request.form.get("outro_tipo_material", "").strip()
        if tipo_material == "Outro" and outro_tipo_material:
            tipo_material = f"Outro - {outro_tipo_material}"

        qualidade_material = request.form["qualidade_material"].strip()
        outra_qualidade_material = request.form.get("outra_qualidade_material", "").strip()
        if qualidade_material == "Outro" and outra_qualidade_material:
            qualidade_material = f"Outro - {outra_qualidade_material}"

        medidas = request.form["medidas"].strip()
        quantidade = request.form["quantidade"].strip()
        observacao_inicio = request.form.get("observacao_inicio", "").strip()

        data_inicio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        conn = get_connection()
        conn.execute("""
            INSERT INTO esperas_material
            (maquina, responsavel_inicio, tipo_material, qualidade_material, medidas, quantidade, observacao_inicio, data_inicio, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            maquina,
            responsavel_inicio,
            tipo_material,
            qualidade_material,
            medidas,
            quantidade,
            observacao_inicio,
            data_inicio,
            "Esperando material"
        ))

        conn.commit()
        conn.close()

        flash("Espera de material registrada com sucesso!")
        return redirect(url_for("espera_material_registrar"))

    return render_template(
        "espera_material/registrar.html",
        maquinas=MAQUINAS,
        tipos_material=TIPOS_MATERIAL,
        qualidades_material=QUALIDADES_MATERIAL
    )


@app.route("/espera-material/consultar", methods=["GET", "POST"])
def espera_material_consultar():
    registros = []
    maquina = ""
    status = ""

    if request.method == "POST":
        maquina = request.form.get("maquina", "").strip()
        status = request.form.get("status", "").strip()

        query = """
            SELECT *
            FROM esperas_material
            WHERE 1 = 1
        """
        parametros = []

        if maquina:
            query += " AND maquina = ?"
            parametros.append(maquina)

        if status:
            query += " AND status = ?"
            parametros.append(status)

        query += " ORDER BY id DESC"

        conn = get_connection()
        registros = conn.execute(query, parametros).fetchall()
        conn.close()

        if not registros:
            flash("Nenhuma espera encontrada com os filtros informados.")

    else:
        conn = get_connection()
        registros = conn.execute("""
            SELECT *
            FROM esperas_material
            WHERE status = 'Esperando material'
            ORDER BY id DESC
        """).fetchall()
        conn.close()

    return render_template(
        "espera_material/consultar.html",
        registros=registros,
        maquinas=MAQUINAS,
        status_espera=STATUS_ESPERA_MATERIAL,
        maquina=maquina,
        status=status
    )


@app.route("/espera-material/atualizar-status", methods=["POST"])
def espera_material_atualizar_status():
    espera_id = request.form["espera_id"]
    cr_material = request.form["cr_material"].strip()
    responsavel_fim = request.form["responsavel_fim"].strip()
    observacao_fim = request.form.get("observacao_fim", "").strip()

    data_fim = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    conn = get_connection()

    espera = conn.execute("""
        SELECT data_inicio
        FROM esperas_material
        WHERE id = ?
    """, (espera_id,)).fetchone()

    if espera is None:
        conn.close()
        flash("Registro de espera não encontrado.")
        return redirect(url_for("espera_material_consultar"))

    formato = "%d/%m/%Y %H:%M:%S"
    inicio = datetime.strptime(espera["data_inicio"], formato)
    fim = datetime.strptime(data_fim, formato)

    diferenca = fim - inicio
    total_segundos = int(diferenca.total_seconds())

    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60

    tempo_total = f"{horas}h {minutos}min"

    conn.execute("""
        UPDATE esperas_material
        SET status = ?,
            cr_material = ?,
            responsavel_fim = ?,
            observacao_fim = ?,
            data_fim = ?,
            tempo_total = ?
        WHERE id = ?
    """, (
        "Material recebido",
        cr_material,
        responsavel_fim,
        observacao_fim,
        data_fim,
        tempo_total,
        espera_id
    ))

    conn.commit()
    conn.close()

    flash("Material recebido registrado com sucesso!")
    return redirect(url_for("espera_material_consultar"))


@app.route("/espera-material/historico", methods=["GET", "POST"])
def espera_material_historico():
    historicos = []
    maquina = ""

    if request.method == "POST":
        maquina = request.form["maquina"].strip()
    else:
        maquina = request.args.get("maquina", "").strip()

    if maquina:
        conn = get_connection()
        historicos = conn.execute("""
            SELECT *
            FROM esperas_material
            WHERE maquina = ?
            ORDER BY id DESC
        """, (maquina,)).fetchall()
        conn.close()

        if not historicos:
            flash("Nenhum histórico encontrado para essa máquina.")

    return render_template(
        "espera_material/historico.html",
        historicos=historicos,
        maquinas=MAQUINAS,
        maquina=maquina
    )


@app.route("/espera-material/relatorio")
def espera_material_relatorio():
    conn = get_connection()
    registros = conn.execute("""
        SELECT *
        FROM esperas_material
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    return render_template(
        "espera_material/relatorio.html",
        registros=registros
    )


@app.route("/espera-material/exportar-historico-csv")
def espera_material_exportar_historico_csv():
    maquina = request.args.get("maquina", "").strip()

    if not maquina:
        flash("Informe a máquina para exportar o histórico.")
        return redirect(url_for("espera_material_historico"))

    conn = get_connection()
    dados = conn.execute("""
        SELECT *
        FROM esperas_material
        WHERE maquina = ?
        ORDER BY id DESC
    """, (maquina,)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID",
        "Máquina",
        "Tipo de Material",
        "Qualidade",
        "Medidas",
        "Quantidade",
        "CR do Material",
        "Responsável Registro",
        "Observação Inicial",
        "Data Início",
        "Responsável Recebimento",
        "Observação Final",
        "Data Recebimento",
        "Tempo Total",
        "Status"
    ])

    for linha in dados:
        writer.writerow([
            linha["id"],
            linha["maquina"],
            linha["tipo_material"],
            linha["qualidade_material"],
            linha["medidas"],
            linha["quantidade"],
            linha["cr_material"],
            linha["responsavel_inicio"],
            linha["observacao_inicio"],
            linha["data_inicio"],
            linha["responsavel_fim"],
            linha["observacao_fim"],
            linha["data_fim"],
            linha["tempo_total"],
            linha["status"]
        ])

    csv_final = "\ufeff" + output.getvalue()

    nome_arquivo = f"historico_espera_material_{maquina}.csv"
    nome_arquivo = (
        nome_arquivo
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "_")
    )

    return Response(
        csv_final,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={nome_arquivo}"
        }
    )


@app.route("/mapa-maquinas")
def mapa_maquinas():
    maquinas_status = []

    conn = get_connection()

    for maquina in MAQUINAS:
        if maquina == "Outra":
            continue

        status_cor = "verde"
        status_texto = "Operacional"
        detalhes = []
        inicio_status = ""

        manutencoes_ativas = conn.execute("""
            SELECT *
            FROM manutencoes
            WHERE maquina = ?
            AND status NOT IN ('Concluída', 'Cancelada')
            ORDER BY id DESC
        """, (maquina,)).fetchall()

        esperas_ativas = conn.execute("""
            SELECT *
            FROM esperas_material
            WHERE maquina = ?
            AND status = 'Esperando material'
            ORDER BY id DESC
        """, (maquina,)).fetchall()

        # Regra vermelha: máquina parada ou em manutenção
        for manutencao in manutencoes_ativas:
            status_manutencao = manutencao["status"].strip().lower()

            if status_manutencao in ["parada", "em manutenção"]:
                status_cor = "vermelho"
                status_texto = manutencao["status"]

                inicio_status = manutencao["data_atualizacao"] or manutencao["data_registro"]

                detalhes.append(
                    f"Manutenção: {manutencao['tipo_manutencao']} - {manutencao['descricao']}"
                )

        # Regra amarela: aguardando manutenção ou peça
        if status_cor != "vermelho":
            for manutencao in manutencoes_ativas:
                status_manutencao = manutencao["status"].strip().lower()

                if status_manutencao in ["aguardando manutenção", "aguardando peça"]:
                    status_cor = "amarelo"
                    status_texto = manutencao["status"]

                    inicio_status = manutencao["data_atualizacao"] or manutencao["data_registro"]

                    detalhes.append(
                        f"Manutenção: {manutencao['tipo_manutencao']} - {manutencao['descricao']}"
                    )

        # Regra amarela: esperando material
        if status_cor != "vermelho":
            for espera in esperas_ativas:
                status_cor = "amarelo"
                status_texto = "Esperando material"

                inicio_status = espera["data_inicio"]

                detalhes.append(
                    f"Material: {espera['tipo_material']} {espera['qualidade_material'] or ''} - {espera['medidas']} - Qtd: {espera['quantidade']}"
                )

        maquinas_status.append({
            "nome": maquina,
            "cor": status_cor,
            "status": status_texto,
            "detalhes": detalhes,
            "inicio_status": inicio_status
        })

    conn.close()

    return render_template(
        "mapa_maquinas/index.html",
        maquinas_status=maquinas_status
    )


@app.route("/espera-material/exportar-csv")
def espera_material_exportar_csv():
    conn = get_connection()
    dados = conn.execute("""
        SELECT *
        FROM esperas_material
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    if linha["status"] == "Esperando material":
        tempo_exportado = calcular_tempo_entre_datas(linha["data_inicio"])
    else:
        tempo_exportado = linha["tempo_total"]    

    writer.writerow([
        "ID",
        "Máquina",
        "Tipo de Material",
        "Qualidade",
        "Medidas",
        "Quantidade",
        "CR do Material",
        "Responsável Registro",
        "Observação Inicial",
        "Data Início",
        "Responsável Recebimento",
        "Observação Final",
        "Data Recebimento",
        "Tempo Total",
        "Status"
    ])

    for linha in dados:
        writer.writerow([
            linha["id"],
            linha["maquina"],
            linha["tipo_material"],
            linha["qualidade_material"],
            linha["medidas"],
            linha["quantidade"],
            linha["cr_material"],
            linha["responsavel_inicio"],
            linha["observacao_inicio"],
            linha["data_inicio"],
            linha["responsavel_fim"],
            linha["observacao_fim"],
            linha["data_fim"],
            tempo_exportado,
            linha["status"]
        ])

    csv_final = "\ufeff" + output.getvalue()

    return Response(
        csv_final,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=relatorio_espera_material.csv"
        }
    )


# ==============================
# Módulo Exportar dados BI
# ==============================

@app.route("/exportar-dados-bi")
def exportar_dados_bi():
    conn = get_connection()

    arquivos = {}

    # =========================
    # 1. RASTREABILIDADE - POSIÇÕES
    # =========================
    posicoes = conn.execute("""
        SELECT 
            id,
            cr,
            posicao,
            quantidade,
            local_atual,
            responsavel,
            observacao,
            data_cadastro,
            ultima_movimentacao
        FROM posicoes
        ORDER BY id DESC
    """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID",
        "CR",
        "Posição",
        "Quantidade",
        "Local Atual",
        "Responsável",
        "Observação",
        "Data Cadastro",
        "Última Movimentação",
        "Horas Sem movimentação"
    ])

    for linha in posicoes:

        horas_sem_movimentacao = calcular_horas_desde_data(linha["ultima_movimentacao"])

        writer.writerow([
            linha["id"],
            linha["cr"],
            linha["posicao"],
            linha["quantidade"],
            linha["local_atual"],
            linha["responsavel"],
            linha["observacao"],
            linha["data_cadastro"],
            linha["ultima_movimentacao"],
            horas_sem_movimentacao
        ])

    arquivos["rastreabilidade_posicoes.csv"] = "\ufeff" + output.getvalue()


    # =========================
    # 2. RASTREABILIDADE - MOVIMENTAÇÕES
    # =========================
    movimentacoes = conn.execute("""
        SELECT 
            id,
            posicao_id,
            cr,
            posicao,
            origem,
            destino,
            responsavel,
            observacao,
            data_hora
        FROM movimentacoes
        ORDER BY id DESC
    """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID Movimentação",
        "ID Lote",
        "CR",
        "Posição",
        "Origem",
        "Destino",
        "Responsável",
        "Observação",
        "Data/Hora"
    ])

    for linha in movimentacoes:
        writer.writerow([
            linha["id"],
            linha["posicao_id"],
            linha["cr"],
            linha["posicao"],
            linha["origem"],
            linha["destino"],
            linha["responsavel"],
            linha["observacao"],
            linha["data_hora"]
        ])

    arquivos["rastreabilidade_movimentacoes.csv"] = "\ufeff" + output.getvalue()


    # =========================
    # 3. MANUTENÇÕES
    # =========================
    manutencoes = conn.execute("""
        SELECT *
        FROM manutencoes
        ORDER BY id DESC
    """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID",
        "Máquina",
        "Tipo de Manutenção",
        "Descrição",
        "Responsável",
        "Status",
        "Observação",
        "Data Registro",
        "Última Atualização",
        "Tempo em Minutos"
    ])

    for linha in manutencoes:
        if linha["status"] in ["Concluída", "Cancelada"] and linha["data_atualizacao"]:
            tempo_manutencao_minutos = calcular_minutos_entre_datas(
                linha["data_registro"],
                linha["data_atualizacao"]
        )
        else:
            tempo_manutencao_minutos = calcular_minutos_entre_datas(
                linha["data_registro"]
            )

        writer.writerow([
            linha["id"],
            linha["maquina"],
            linha["tipo_manutencao"],
            linha["descricao"],
            linha["responsavel"],
            linha["status"],
            linha["observacao"],
            linha["data_registro"],
            linha["data_atualizacao"],
            tempo_manutencao_minutos
        ])

    arquivos["manutencoes.csv"] = "\ufeff" + output.getvalue()


    # =========================
    # 4. ESPERAS DE MATERIAL
    # =========================
    esperas = conn.execute("""
        SELECT *
        FROM esperas_material
        ORDER BY id DESC
    """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID",
        "Máquina",
        "Tipo de Material",
        "Qualidade",
        "Medidas",
        "Quantidade",
        "CR do Material",
        "Responsável Registro",
        "Observação Inicial",
        "Data Início",
        "Responsável Recebimento",
        "Observação Final",
        "Data Recebimento",
        "Tempo Total",
        "Status"
    ])

    for linha in esperas:
        if linha["status"] == "Esperando material":
            tempo_exportado = calcular_tempo_entre_datas(linha["data_inicio"])
        else:
            tempo_exportado = linha["tempo_total"]
        writer.writerow([
            linha["id"],
            linha["maquina"],
            linha["tipo_material"],
            linha["qualidade_material"],
            linha["medidas"],
            linha["quantidade"],
            linha["cr_material"],
            linha["responsavel_inicio"],
            linha["observacao_inicio"],
            linha["data_inicio"],
            linha["responsavel_fim"],
            linha["observacao_fim"],
            linha["data_fim"],
            tempo_exportado,
            linha["status"]
        ])

    arquivos["esperas_material.csv"] = "\ufeff" + output.getvalue()

    conn.close()


    # =========================
    # CRIA O ZIP EM MEMÓRIA
    # =========================
    os.makedirs(PASTA_EXPORTS_BI, exist_ok=True)

    for nome_arquivo, conteudo in arquivos.items():
        caminho_arquivo = os.path.join(PASTA_EXPORTS_BI, nome_arquivo)

        with open(caminho_arquivo, "w", encoding="utf-8-sig", newline="") as arquivo:
            arquivo.write(conteudo.replace("\ufeff", ""))

    flash("Dados BI exportados com sucesso para a pasta da rede.")
    return redirect(url_for("index"))






# =============================================================

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)