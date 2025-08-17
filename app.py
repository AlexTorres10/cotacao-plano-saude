import streamlit as st
import pandas as pd
from supabase import create_client
import bcrypt
from datetime import datetime, timezone, timedelta
import random
import uuid
import base64
# --- Conexão com Supabase ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Configuração inicial do app ---
st.set_page_config(page_title="CoteFácil Saúde", layout="centered")

limite = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
supabase.table("usuarios") \
    .update({"sessao_ativa": False, "sessao_token": None}) \
    .eq("sessao_ativa", True) \
    .lt("ultima_atividade", limite) \
    .execute()

def get_base64_of_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()
    
img_base64 = get_base64_of_image("cotefacil.jpg")

# --- Estilo CSS ---
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(255,255,255,0.8), rgba(255,255,255,0.8)), url("data:image/png;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}
    </style>
    """,
    unsafe_allow_html=True
)
# --- Funções auxiliares ---
def formatar_validade(yyyymm):
    meses_pt = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
        "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
        "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
    }
    try:
        ano, mes = yyyymm.split('-')
        nome_mes = meses_pt.get(mes.zfill(2), mes)
        return f"{nome_mes} de {ano}"
    except:
        return yyyymm


def idade_na_faixa(idade, faixa_etaria):
    if '+' in faixa_etaria:
        return idade >= int(faixa_etaria.replace('+', '').strip())
    faixa = list(map(int, faixa_etaria.split('-')))
    return faixa[0] <= idade <= faixa[1]


def atualizar_sessao(username):
    agora = datetime.now(timezone.utc).isoformat()
    supabase.table("usuarios").update({
        "sessao_ativa": True,
        "ultima_atividade": agora
    }).eq("username", username).execute()


# --- Tela de redefinição de senha ---
def tela_reset_senha():
    st.title("Redefinir Senha")
    email = st.text_input("Digite seu e-mail cadastrado")
    if st.button("Enviar nova senha"):
        result = supabase.table("usuarios").select("*").eq("email", email).execute()
        user_data = result.data
        if not user_data:
            st.error("E-mail não encontrado.")
        else:
            nova_senha = ''.join(random.choices("abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=8))
            hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
            supabase.table("usuarios").update({
                "password_hash": hash,
                "sessao_ativa": False
            }).eq("email", email).execute()
            st.success(f"Sua nova senha temporária é: **{nova_senha}**. Altere após o login.")

def agora_iso():
    return datetime.now(timezone.utc).isoformat()

def gerar_token():
    return uuid.uuid4().hex

def marcar_login(supabase, username):
    token = gerar_token()
    supabase.table("usuarios").update({
        "sessao_ativa": True,
        "sessao_token": token,
        "ultima_atividade": agora_iso(),
        # opcional:
        # "sessao_expira_em": datetime.now(timezone.utc) + timedelta(days=30)
    }).eq("username", username).execute()
    return token

def marcar_logout(supabase, username):
    supabase.table("usuarios").update({
        "sessao_ativa": False,
        "sessao_token": None
    }).eq("username", username).execute()

def checar_sessao_unica(supabase, username, token_local):
    """Retorna True se a sessão ainda é válida neste dispositivo."""
    res = supabase.table("usuarios").select("sessao_token,sessao_ativa").eq("username", username).single().execute()
    if not res.data:
        return False
    row = res.data
    if not row.get("sessao_ativa"):
        return False
    return (row.get("sessao_token") == token_local)

def heartbeat(supabase, username):
    """Atualiza o timestamp para controle de inatividade/limpeza."""
    supabase.table("usuarios").update({
        "ultima_atividade": agora_iso()
    }).eq("username", username).execute()

if st.session_state.get("logged_in"):
    valido = checar_sessao_unica(
        supabase,
        st.session_state["username"],
        st.session_state.get("sessao_token")
    )
    if not valido:
        st.error("Sua sessão foi encerrada porque houve login em outro dispositivo.")
        st.session_state.clear()
        st.rerun()
    else:
        # Mantém a sessão viva (e permite sua rotina de limpar inativos)
        heartbeat(supabase, st.session_state["username"])

# --- Tela de login ---
def login():
    
    st.title("Login - CoteFácil Saúde")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    # col1, col2 = st.columns([2, 1])
    # with col1:
    #     entrar = st.button("Entrar")
    # with col2:
    #     esqueci = st.button("Esqueci minha senha")
    entrar = st.button("Entrar")

    st.markdown(
        """
        <div style="background-color:#f0f2f6;padding:20px;border-radius:10px;margin-bottom:30px;">
            <h4 style="margin-top:0;">Compare os principais planos de saúde em um só lugar.<br>
            <span style="color:#0a66c2;">Rápido, fácil e 100% online.</span></h4>
            <ul style="list-style: none; padding-left: 0;">
                <li>✔️ Sem planilhas</li>
                <li>✔️ Sem confusão</li>
                <li>✔️ Só as melhores opções pra você</li>
            </ul>
            <p style="font-weight:bold;color:#0a66c2;">CoteFácil Saúde — sua escolha, sem complicação.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    limite = (datetime.now() - timedelta(minutes=20)).isoformat()

    # Atualiza todos que estão com sessão ativa e inativos há mais de 20 min
    supabase.table("usuarios") \
        .update({"sessao_ativa": False}) \
        .eq("sessao_ativa", True) \
        .lt("ultima_atividade", limite) \
        .execute()
    if entrar:
        if not username or not password:
            st.warning("Por favor, preencha todos os campos.")
            return

        result = supabase.table("usuarios").select("*").eq("username", username).execute()
        data = result.data

        if not data:
            st.error("Usuário não encontrado.")
            return

        user = data[0]
        if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            if user.get("sessao_ativa"):
                st.error("Este usuário já está com uma sessão ativa em outro dispositivo.")
                return

            # Marca a sessão como ativa
            atualizar_sessao(username)

            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            token = marcar_login(supabase, username)
            st.session_state["sessao_token"] = token
            st.rerun()
        else:
            st.error("Senha incorreta.")

    # if esqueci:
    #     st.session_state["tela"] = "reset"
    #     st.rerun()

# --- Controle de telas ---
if st.session_state.get("tela") == "reset":
    tela_reset_senha()
    st.stop()

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()
    st.stop()

# --- Conteúdo principal ---
st.title("CoteFácil Saúde")
st.sidebar.success(f"Logado como: {st.session_state['username']}")
if st.sidebar.button("Sair"):
    marcar_logout(supabase, st.session_state["username"])
    st.session_state.clear()
    st.rerun()

# --- Entrada do usuário --- (per capita)
st.markdown("### Cotação de Planos de Saúde")
qtd = st.number_input("Quantas pessoas serão incluídas?", min_value=1, max_value=10, step=1, value=1)

# Campos de idade dinâmicos
idades = []
cols_idades = st.columns(min(qtd, 4))  # até 4 por linha, depois quebra
for i in range(qtd):
    col = cols_idades[i % 4]
    with col:
        idade_i = st.number_input(f"Idade da pessoa {i+1}", min_value=0, max_value=120, step=1, key=f"idade_{i}")
        idades.append(int(idade_i))

# Filtro de faixa de preço (média per capita)
faixa_de_preco = st.slider(
    "Filtro por **média per capita (R$)** - Valor por cada pessoa incluída no plano",
    min_value=100.0, max_value=4000.0,
    value=(100.0, 4000.0), step=1.0
)

# Carrega dados
df = pd.read_excel("planos_de_saude_unificado.xlsx", engine="openpyxl")

# Filtros de Tipo (checkboxes lado a lado)
st.markdown("### Tipo de Plano")
tipos_disponiveis = sorted(df["Tipo"].dropna().unique().tolist())
cols_tipo = st.columns(len(tipos_disponiveis) if tipos_disponiveis else 1)
tipos_selecionados = []
for i, tipo in enumerate(tipos_disponiveis):
    if cols_tipo[i].checkbox(tipo, value=True, key=f"tipo_{i}"):
        tipos_selecionados.append(tipo)
if not tipos_selecionados:
    tipos_selecionados = tipos_disponiveis[:]  # fallback

# Filtros de Empresa (checkboxes lado a lado)
st.markdown("### Empresa")
empresas = sorted(df["Empresa"].dropna().unique().tolist())
cols_emp = st.columns(len(empresas) if empresas else 1)
empresas_selecionadas = []
for i, emp in enumerate(empresas):
    if cols_emp[i].checkbox(emp, value=True, key=f"emp_{i}"):
        empresas_selecionadas.append(emp)
if not empresas_selecionadas:
    empresas_selecionadas = empresas[:]  # fallback

def idade_na_faixa(idade, faixa):
    faixa = str(faixa).strip()
    if '+' in faixa:
        return idade >= int(faixa.replace('+', '').strip())
    # formatos comuns: "00 - 18", "00 a 18", "0-18"
    faixa = faixa.replace('a', '-').replace('A', '-').replace(' ', '')
    ini, fim = faixa.split('-')
    return int(ini) <= idade <= int(fim)

# Normaliza Validade para período mensal seguro
# Validade esperada como "YYYY-MM". Coerção para datas e comparação mensal.
val_raw = df["Validade"].astype(str).str.strip()
df["_val_dt"] = pd.to_datetime(val_raw + "-01", errors="coerce")  # 1º dia do mês
hoje_m = pd.to_datetime(datetime.now().strftime("%Y-%m") + "-01")

# Aplica filtros básicos antes da cotação
df_base = df[
    df["Tipo"].isin(tipos_selecionados) &
    df["Empresa"].isin(empresas_selecionadas)
].copy()

# Monta cotação por plano (Empresa, Tipo, Abrangência, Validade)
# Para cada plano, precisa existir 1 linha por idade informada (faixa compatível).
grupos = ["Empresa", "Tipo", "Abrangência", "Validade", "_val_dt", "Associado"]
resultados = []
for chave, bloco in df_base.groupby(grupos):
    empresa, tipo, abr, validade, val_dt, assoc = chave
    precos = []
    ok = True
    for idade in idades:
        # filtra linhas do bloco que atendem a essa idade
        match = bloco[bloco["Idade"].apply(lambda x: idade_na_faixa(idade, x))]
        if match.empty:
            ok = False
            break
        # preço para essa idade (se houver mais de uma linha, pega a primeira)
        preco = match.iloc[0]["Preço"]
        if pd.isna(preco):
            ok = False
            break
        precos.append(float(preco))
    if not ok:
        continue

    total = sum(precos)
    media = total / len(idades) if idades else 0.0
    resultados.append({
        "Empresa": empresa,
        "Tipo": tipo,
        "Abrangência": abr,
        "Validade": validade,
        "_val_dt": val_dt,
        "Total": total,
        "Média per capita": media,
        "Detalhe preços": " + ".join([f"R$ {p:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".") for p in precos])
    })

# DataFrame agregado dos planos
if st.button("Fazer cotação"):
    atualizar_sessao(st.session_state["username"])

    if not resultados:
        st.warning("Nenhum plano atende a todas as idades informadas com os filtros atuais.")
    else:
        df_cot = pd.DataFrame(resultados)

        # Filtra pela MÉDIA per capita (como você pediu)
        df_cot = df_cot[
            (df_cot["Média per capita"] >= faixa_de_preco[0]) &
            (df_cot["Média per capita"] <= faixa_de_preco[1])
        ]

        if df_cot.empty:
            st.warning("Nenhum plano dentro da faixa de **média per capita** selecionada.")
        else:
            # Ordena do maior ao menor pela média per capita
            df_cot = df_cot.sort_values("Média per capita", ascending=False)

            # Formata valores
            df_cot_fmt = df_cot.copy()
            df_cot_fmt["Total"] = df_cot_fmt["Total"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
            df_cot_fmt["Média per capita"] = df_cot_fmt["Média per capita"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
            # Formata Validade para "Mês de AAAA"
            meses_pt = {
                "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
                "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
                "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
            }
            def formatar_validade(yyyymm):
                try:
                    ano, mes = str(yyyymm).split("-")
                    return f"{meses_pt.get(mes.zfill(2), mes)} de {ano}"
                except:
                    return yyyymm
            df_cot_fmt["Validade"] = df_cot_fmt["Validade"].astype(str).str.strip().apply(formatar_validade)

            # Separa vencidos x válidos usando datas (sem erro de string)
            vencidos_mask = df_cot["_val_dt"].notna() & (df_cot["_val_dt"] < hoje_m)
            df_validos = df_cot_fmt.loc[~vencidos_mask].drop(columns=["_val_dt"])
            df_vencidos = df_cot_fmt.loc[vencidos_mask].drop(columns=["_val_dt"])

            st.markdown("### ✅ Planos válidos")
            st.dataframe(
                df_validos.reset_index(drop=True),
                use_container_width=True,
                hide_index=True
            )

            if not df_vencidos.empty:
                st.warning("⚠️ Os planos abaixo perderam a validade e serão atualizados.")
                st.dataframe(
                    df_vencidos.reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )

            # Explicações
            st.markdown("""
            ### 🔍 Entenda a Coparticipação
            - **Coparticipação Parcial:** o plano cobre a maioria dos procedimentos, e você paga apenas uma parte de consultas ou exames.
            - **Coparticipação Total:** você paga integralmente por cada procedimento realizado, com o plano oferecendo apenas cobertura de internação e exames de alto custo.

            ### 🛏️ Enfermaria x Apartamento
            - **Enfermaria:** quarto coletivo, geralmente com 2 ou mais pacientes.
            - **Apartamento:** quarto individual, com maior privacidade e conforto.
            """)
