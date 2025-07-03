import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cotação de Planos de Saúde", layout="centered")

st.title("Cotação de Planos de Saúde")

# Upload ou carregamento do Excel
df = pd.read_excel("planos_de_saude_unificado.xlsx", engine="openpyxl")

# Entrada do usuário
idade = st.number_input("Informe sua idade", min_value=0, max_value=120, step=1)

if st.button("Fazer cotação"):
    # Trata faixas com '59+'
    def idade_na_faixa(idade, faixa_etaria):
        if '+' in faixa_etaria:
            min_idade = int(faixa_etaria.replace('+', '').strip())
            return idade >= min_idade
        else:
            partes = faixa_etaria.replace('anos', '').replace(' ', '').split('a')
            if len(partes) == 2:
                return int(partes[0]) <= idade <= int(partes[1])
            return False

    # Filtra os planos compatíveis com a idade
    planos_filtrados = df[df["Faixa Etária"].apply(lambda x: idade_na_faixa(idade, x))]

    if planos_filtrados.empty:
        st.warning("Nenhum plano encontrado para essa faixa etária.")
    else:
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

        # Mostra os planos
        st.dataframe(planos_filtrados.reset_index(drop=True))
