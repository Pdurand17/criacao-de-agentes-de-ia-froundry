import streamlit as st


st.title('isso é um titulo')

nome = st.text_input('nome: ')
idade = st.number_input('idade: ', value = 0)
curso = st.text_input('curso: ')

if nome and idade:
    if st.button('mostrar'):
        st.write(nome)
        st.write(idade)
        st.write(curso)

# ctrl + " -> terminal abre
# streamlit run app.py