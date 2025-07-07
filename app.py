import streamlit as st
import pandas as pd
from supabase import create_client
import bcrypt
from datetime import datetime
import calendar

# --- Conexão com o Supabase ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Cotação de Planos de Saúde", layout="centered")

def login():
    st.title("Login")

    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if not username or not password:
            st.warning("Por favor, preencha todos os campos.")
            return

        # Consulta o usuário no Supabase
        result = supabase.table("usuarios").select("*").eq("username", username).execute()
        data = result.data

        result = supabase.table("usuarios").select("*").execute()
        data_b = result.data

        if not data:
            st.error("Usuário não encontrado.")
            return

        user = data[0]
        stored_hash = user["password_hash"].encode()

        if bcrypt.checkpw(password.encode(), stored_hash):
            st.success("Login bem-sucedido!")
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Senha incorreta.")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()
    st.stop()

st.title("Cotação de Planos de Saúde")

# Upload ou carregamento do Excel
df = pd.read_excel("planos_de_saude_unificado.xlsx", engine="openpyxl")
# Entrada do usuário
idade = st.number_input("Informe sua idade", min_value=0, max_value=120, step=1)

st.sidebar.success(f"Logado como: {st.session_state['username']}")
if st.sidebar.button("Sair"):
    del st.session_state["logged_in"]
    st.rerun()

import locale

# Tenta usar o locale brasileiro
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR')  # alternativa para Windows
    except:
        st.warning("⚠️ Não foi possível aplicar o idioma português ao calendário.")

def formatar_validade(yyyymm):
    try:
        ano, mes = map(int, yyyymm.split('-'))
        data_falsa = datetime(ano, mes, 1)
        nome_mes = data_falsa.strftime('%B').capitalize()
        return f"{nome_mes} de {ano}"
    except:
        return yyyymm

if st.button("Fazer cotação"):
    # Trata faixas com '59+'
    def idade_na_faixa(idade, faixa_etaria):
        if '+' in faixa_etaria:
            min_idade = int(faixa_etaria.replace('+', '').strip())
            return idade >= min_idade
        else:
            partes = faixa_etaria.split('-')
            return int(partes[0]) <= idade <= int(partes[1])
        
    hoje = datetime.today()
    mes_atual = hoje.strftime("%Y-%m")

    # Converter colunas de validade para string (por segurança)
    df["Validade"] = df["Validade"].astype(str)
    # Filtra os planos compatíveis com a idade
    planos_filtrados = df[df["Idade"].apply(lambda x: idade_na_faixa(idade, x))]

    if planos_filtrados.empty:
        st.warning("Nenhum plano encontrado para essa faixa etária.")
    else:
        colunas_monetarias = ["Enfermaria", "Apartamento"]

        for col in colunas_monetarias:
            planos_filtrados[col] = planos_filtrados[col].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".") if pd.notnull(x) and isinstance(x, (int, float)) else x
            )

        # Mostra os planos
        planos_vencidos = planos_filtrados[planos_filtrados["Validade"] < mes_atual]

        # Atualiza o campo 'Validade' para exibição
        planos_filtrados["Validade"] = planos_filtrados["Validade"].apply(formatar_validade)
        planos_vencidos["Validade"] = planos_vencidos["Validade"].apply(formatar_validade)

        # Mostrar os planos ainda válidos
        st.markdown("### ✅ Planos válidos para sua idade:")
        st.dataframe(planos_filtrados.reset_index(drop=True), use_container_width=True, hide_index=True)

        # Mostrar os planos vencidos, se houver
        if not planos_vencidos.empty:
            st.warning("⚠️ Os planos abaixo perderam a validade e estão com valores possivelmente desatualizados.")
            st.dataframe(planos_vencidos.reset_index(drop=True), use_container_width=True, hide_index=True)
        # Explicação sobre coparticipação
        st.markdown("""
        ### 🔍 Entenda a Coparticipação
        - **Coparticipação Parcial:** o plano cobre a maioria dos procedimentos, e você paga apenas uma parte de consultas ou exames.
        - **Coparticipação Total:** você paga integralmente por cada procedimento realizado, com o plano oferecendo apenas cobertura de internação e exames de alto custo.
        """)

        # Explicação sobre enfermaria x apartamento
        st.markdown("""
        ### 🛏️ Enfermaria x Apartamento
        - **Enfermaria:** quarto coletivo, geralmente com 2 ou mais pacientes.
        - **Apartamento:** quarto individual, com maior privacidade e conforto.
        """)

        
