import pandas as pd
import streamlit as st

# Carregar o Excel com os planos
df_planos = pd.read_excel("planos_de_saude_unificado.xlsx")  # ajuste o caminho se necessário

st.title("Consulta de Planos de Saúde por Idade")
idade = st.number_input("Digite sua idade:", min_value=0, max_value=120, step=1)

st.markdown("""
**Coparticipação:**
- **Copartipação Parcial:** Você paga parte do valor quando usa o serviço (ex: consultas, exames simples).
- **Copartipação Total:** Você paga a maior parte dos procedimentos, inclusive alguns de alto custo.
""")
# Leitura do Excel consolidado
@st.cache_data
def carregar_dados():
    df = pd.read_excel("planos_de_saude_unificado.xlsx")
    return df

df = carregar_dados()

# Entrada da idade
idade = st.number_input("Informe sua idade:", min_value=0, max_value=120, step=1)

# Função para verificar se idade pertence à faixa
def idade_na_faixa(idade_pessoa, faixa):
    if faixa.endswith('+'):
        return idade_pessoa >= int(faixa.replace('+', ''))
    elif '-' in faixa:
        partes = faixa.split('-')
        return int(partes[0]) <= idade_pessoa <= int(partes[1])
    return False

# Filtrar os planos pela idade informada
df_filtrado = df[df['Idade'].apply(lambda faixa: idade_na_faixa(idade, faixa))]

if not df_filtrado.empty:
    st.success(f"Planos encontrados para {idade} anos:")
    st.dataframe(df_filtrado.reset_index(drop=True))
else:
    st.warning("Nenhum plano encontrado para essa idade.")
