import streamlit as st
import pandas as pd
from supabase import create_client
import bcrypt
from datetime import datetime, timezone, timedelta
import random


# --- Conexão com Supabase ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Configuração inicial do app ---
st.set_page_config(page_title="Cotação de Planos de Saúde", layout="centered")

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

# --- Tela de login ---
def login():
    st.title("Login - Cotação de Planos de Saúde")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    # col1, col2 = st.columns([2, 1])
    # with col1:
    #     entrar = st.button("Entrar")
    # with col2:
    #     esqueci = st.button("Esqueci minha senha")
    entrar = st.button("Entrar")

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
st.title("Cotação de Planos de Saúde")
st.sidebar.success(f"Logado como: {st.session_state['username']}")
if st.sidebar.button("Sair"):
    supabase.table("usuarios").update({"sessao_ativa": False}).eq("username", st.session_state["username"]).execute()
    del st.session_state["logged_in"]
    del st.session_state["username"]
    st.rerun()

# --- Entrada do usuário ---
idade = st.number_input("Informe sua idade", min_value=0, max_value=120, step=1)
faixa_de_preco = st.slider(
    "Faixa de preço per capita (R$)",
    min_value=100.0,
    max_value=4000.0,
    value=(100.0, 4000.0),
    step=1.0
)

df = pd.read_excel("planos_de_saude_unificado.xlsx", engine="openpyxl")
st.markdown("### Tipo de Plano:")
tipos_disponiveis = df["Tipo"].dropna().unique().tolist()
tipos_disponiveis.sort()
cols = st.columns(len(tipos_disponiveis))
tipos_selecionados = []

for i, tipo in enumerate(tipos_disponiveis):
    if cols[i].checkbox(tipo, value=True):
        tipos_selecionados.append(tipo)

# --- Interface: Filtro por Empresa ---
st.markdown("### Empresa:")
empresas = sorted(df["Empresa"].dropna().unique())
cols_empresa = st.columns(len(empresas))
empresas_selecionadas = []

for i, empresa in enumerate(empresas):
    if cols_empresa[i].checkbox(empresa, value=True):
        empresas_selecionadas.append(empresa)


if st.button("Fazer cotação"):
    atualizar_sessao(st.session_state["username"])
    df = pd.read_excel("planos_de_saude_unificado.xlsx", engine="openpyxl")
    df["Validade"] = df["Validade"].astype(str)

    hoje = datetime.today().strftime("%Y-%m")
    planos_filtrados = df[df["Idade"].apply(lambda x: idade_na_faixa(idade, x))]

    # --- Aplicar Filtros ---
    planos_filtrados = planos_filtrados[
        (planos_filtrados["Preço"] >= faixa_de_preco[0]) &
        (planos_filtrados["Preço"] <= faixa_de_preco[1]) &
        (planos_filtrados["Tipo"].isin(tipos_selecionados)) &
        (planos_filtrados["Empresa"].isin(empresas_selecionadas))
    ]

    if planos_filtrados.empty:
        st.warning("Nenhum plano encontrado para essa faixa etária.")
    else:
        planos_filtrados = planos_filtrados.sort_values("Preço", ascending=False)
        planos_filtrados['Preço'] = planos_filtrados['Preço'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".") if pd.notnull(x) and isinstance(x, (int, float)) else x
        )

        planos_vencidos = planos_filtrados[planos_filtrados["Validade"] < hoje]

        planos_filtrados["Validade"] = planos_filtrados["Validade"].apply(formatar_validade)
        planos_vencidos["Validade"] = planos_vencidos["Validade"].apply(formatar_validade)

        st.markdown("### ✅ Planos válidos:")
        st.dataframe(planos_filtrados.reset_index(drop=True),
            use_container_width=True,
            hide_index=True
        )

        if not planos_vencidos.empty:
            st.warning("⚠️ Os planos abaixo perderam a validade e estão com valores possivelmente desatualizados.")
            st.dataframe(planos_filtrados.reset_index(drop=True),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("""
        ### 🔍 Entenda a Coparticipação
        - **Coparticipação Parcial:** o plano cobre a maioria dos procedimentos, e você paga apenas uma parte de consultas ou exames.
        - **Coparticipação Total:** você paga integralmente por cada procedimento realizado, com o plano oferecendo apenas cobertura de internação e exames de alto custo.
        
        ### 🛏️ Enfermaria x Apartamento
        - **Enfermaria:** quarto coletivo, geralmente com 2 ou mais pacientes.
        - **Apartamento:** quarto individual, com maior privacidade e conforto.
        """)
