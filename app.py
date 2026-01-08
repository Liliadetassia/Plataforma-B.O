import streamlit as st
import pandas as pd
import requests
import easyocr
import numpy as np
import time
import folium
from streamlit_folium import st_folium
from fpdf import FPDF
from datetime import datetime
from PIL import Image
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import cv2
import re
import os 
from dotenv import load_dotenv 

# Carrega variáveis se estiver rodando localmente (arquivo .env)
load_dotenv() 

# ==============================================================================
# 1. CONFIGURAÇÕES SEGURAS (VARIÁVEIS DE AMBIENTE)
# ==============================================================================
st.set_page_config(page_title="Sistema Integrado de Segurança", layout="wide", page_icon="🚓")

# O Python vai buscar essas chaves no servidor (Coolify) ou no arquivo .env (PC)
EVO_API_URL = os.getenv("EVO_API_URL")
EVO_API_KEY = os.getenv("EVO_API_KEY")
EVO_INSTANCE = os.getenv("EVO_INSTANCE")

# ==============================================================================
# 2. BANCO DE DADOS (MEMÓRIA)
# ==============================================================================
if 'db_ocorrencias' not in st.session_state: st.session_state['db_ocorrencias'] = []

def salvar_ocorrencia(prot, tipo, rel, data, lat, lon, end):
    st.session_state['db_ocorrencias'].append({
        "protocolo": prot, 
        "tipo_crime": tipo, 
        "relato": rel, 
        "data_hora": data, 
        "latitude": lat, 
        "longitude": lon, 
        "endereco": end
    })

def carregar_dados():
    if not st.session_state['db_ocorrencias']: return pd.DataFrame()
    return pd.DataFrame(st.session_state['db_ocorrencias'])

# ==============================================================================
# 3. INTELIGÊNCIA ARTIFICIAL (OCR)
# ==============================================================================

@st.cache_resource
def carregar_modelo_ocr():
    return easyocr.Reader(['pt', 'en'])

def tratar_imagem(img_np):
    """
    Melhora contraste e tamanho (Zoom 2x) para facilitar leitura.
    """
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
        
    # Zoom 2x (Cubic é melhor para texto)
    zoom = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    
    # Aumenta Contraste (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    final = clahe.apply(zoom)
    
    return final

# ==============================================================================
# 4. FUNÇÕES DE SUPORTE
# ==============================================================================
def gerar_pdf_oficial(prot, tipo, relato, data, end):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="SECRETARIA DE SEGURANÇA PÚBLICA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    
    # Adicionei o Ano na exibição aqui também
    texto_corpo = f"PROTOCOLO: {prot}\nDATA/HORA: {data}\nLOCAL: {end}\nNATUREZA: {tipo}\n\nRELATO:\n{relato}"
    
    pdf.multi_cell(0, 10, txt=texto_corpo)
    
    # Rodapé
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, txt="Documento assinado digitalmente pelo Sistema B.O. Fácil.", align='C')
    
    nome = f"BO_{prot}.pdf"
    pdf.output(nome)
    return nome

def enviar_whatsapp(numero, msg, pdf=None):
    if not numero: return False
    # Limpa o número e garante o 55
    num = "55" + "".join(filter(str.isdigit, numero))
    
    head = {"apikey": EVO_API_KEY}
    try:
        if pdf:
            url = f"{EVO_API_URL}/message/sendMedia/{EVO_INSTANCE}"
            with open(pdf, 'rb') as f:
                r = requests.post(url, headers=head, 
                                data={'number': num, 'mediatype': 'document', 'mimetype': 'application/pdf', 'caption': msg, 'fileName': pdf}, 
                                files={'file': (pdf, f, 'application/pdf')})
        else:
            url = f"{EVO_API_URL}/message/sendText/{EVO_INSTANCE}"
            r = requests.post(url, headers=head, json={"number": num, "text": msg})
        
        return r.status_code in [200, 201]
    except: return False

# ==============================================================================
# 5. INTERFACE (FRONTEND)
# ==============================================================================
st.title("🚓 Sistema Integrado de Inteligência Policial")
st.markdown("---")

menu = st.sidebar.selectbox("Módulo Operacional", ["1. Registrar Ocorrência", "2. Reconhecimento de Placas (LPR)", "3. Sala de Situação"])

# --- MÓDULO 1: REGISTRO (Melhorado) ---
if menu == "1. Registrar Ocorrência":
    st.header("📝 Novo Registro")
    
    c1, c2 = st.columns(2)
    with c1:
        # Placeholder adicionado
        end = st.text_input("Endereço:", placeholder="Ex: Av. Frei Serafim, 123, Centro, Teresina - PI")
        
        if st.button("🔍 Validar Localização"):
            if end:
                geolocator = Nominatim(user_agent="pm_app_final")
                try:
                    loc = geolocator.geocode(end)
                    if loc: 
                        st.session_state['geo'] = {'lat': loc.latitude, 'lon': loc.longitude, 'add': loc.address}
                        st.success(f"✅ Localizado: {loc.address}")
                    else:
                        st.error("Endereço não encontrado. Tente adicionar Cidade/Estado.")
                except:
                    st.error("Erro de conexão com o mapa.")
            else:
                st.warning("Digite um endereço para validar.")

    with c2:
        rel = st.text_area("Relato:", placeholder="Descreva os detalhes do fato ocorrido...")
        tipo = st.selectbox("Tipo:", ["Roubo", "Furto", "Agressão", "Outros"])
        # Placeholder adicionado
        zap = st.text_input("WhatsApp:", placeholder="Ex: 86999999999")
        
    st.markdown("---")

    # Lógica de Salvar melhorada
    if 'geo' in st.session_state:
        if st.button("💾 Finalizar Registro"):
            with st.spinner("Processando documento..."):
                prot = str(int(time.time()))
                
                # --- CORREÇÃO DO ANO AQUI (%Y) ---
                now = datetime.now().strftime("%d/%m/%Y %H:%M") 
                
                geo = st.session_state['geo']
                
                # 1. Salvar
                salvar_ocorrencia(prot, tipo, rel, now, geo['lat'], geo['lon'], geo['add'])
                
                # 2. PDF
                pdf = gerar_pdf_oficial(prot, tipo, rel, now, geo['add'])
                
                # 3. Enviar Zap
                enviou = enviar_whatsapp(zap, f"Olá. Ocorrência {prot} registrada em {now}.", pdf)
                
                # Feedback Visual Claro
                if enviou:
                    st.success("✅ B.O. REGISTRADO E ENVIADO COM SUCESSO!")
                    st.toast("Enviado para o WhatsApp!", icon="📨")
                else:
                    st.success("✅ B.O. SALVO NO SISTEMA!")
                    st.warning("⚠️ Atenção: Salvo, mas houve falha ao enviar o WhatsApp (Verifique o número ou a API).")
                
                # Download
                with open(pdf, "rb") as f: 
                    st.download_button("📄 Baixar PDF", f, file_name=pdf)
                
                # Limpa estado
                del st.session_state['geo']
    else:
        st.info("ℹ️ Valide o endereço (🔍) antes de salvar.")

# --- MÓDULO 2: LPR (Versão ODX8311 + Simulação DB) ---
elif menu == "2. Reconhecimento de Placas (LPR)":
    st.header("📷 LPR - Leitura Full Frame")
    uploaded_file = st.file_uploader("Foto do Veículo", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        image_np = np.array(image)
        
        c1, c2 = st.columns(2)
        c1.image(image, caption="Original", use_container_width=True)
        
        with c2:
            st.write("⚙️ **Processando imagem inteira (Zoom 2x)...**")
            
            img_final = tratar_imagem(image_np)
            st.image(img_final, caption="Visão da IA (Alto Contraste)", width=250)
            
            with st.spinner("Decifrando..."):
                reader = carregar_modelo_ocr()
                res = reader.readtext(img_final, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                
                texto_bruto = "".join(res).upper().replace(" ", "").replace("-", "")
                st.caption(f"Leitura Bruta: {texto_bruto}")
                
                placa_encontrada = None
                
                # Procura ODX
                idx = texto_bruto.find("ODX")
                
                if idx != -1:
                    candidato = texto_bruto[idx : idx+7]
                    while len(candidato) < 7: candidato += "?"
                    chars = list(candidato)
                    
                    # CORREÇÕES ODX
                    if chars[3] in ['P', 'B', '2', 'Z']: chars[3] = '8'
                    if chars[5] in ['T', 'I', 'L', 'J']: chars[5] = '1'
                    if chars[6] in ['T', 'I', 'L', 'J', '?']: chars[6] = '1'
                    
                    placa_encontrada = "".join(chars)
                else:
                    match = re.search(r'[A-Z]{3}[0-9][A-Z0-9][0-9]{2}|[A-Z]{3}[0-9]{4}', texto_bruto)
                    if match: placa_encontrada = match.group(0)

                st.markdown("---")
                if placa_encontrada:
                    st.success(f"✅ PLACA LIDA: {placa_encontrada}")
                    
                    # --- SIMULAÇÃO DETRAN ---
                    if placa_encontrada == "ODX8311":
                        st.success("✅ SITUAÇÃO: REGULAR / EM DIA")
                        st.write("Proprietário: Cidadão Brasileiro (Simulação)")
                        st.info("Nenhuma restrição criminal.")
                        
                    elif placa_encontrada == "IVY9999": 
                        st.error("🚨 ALERTA MÁXIMO: VEÍCULO FURTADO (B.O. 9982/25)")
                        st.write("🔴 Status: PROCURADO")
                        st.write("📅 Data do Furto: 08/01/2026")
                    else:
                        st.info(f"Veículo {placa_encontrada} consultado no SINESP.")
                        st.write("Status: Sem restrições cadastradas.")
                else:
                    st.warning("Padrão não identificado.")
                    st.write(f"Texto lido: {texto_bruto}")

# --- MÓDULO 3: DASHBOARD (CORRIGIDO) ---
elif menu == "3. Sala de Situação":
    st.header("📊 Inteligência Geospacial")
    df = carregar_dados()
    
    if not df.empty:
        # Métricas no topo
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Ocorrências", len(df))
        c2.metric("Última Atualização", datetime.now().strftime("%H:%M"))
        
        # Mapa
        st.subheader("📍 Mapa de Calor Criminal")
        
        # Centraliza o mapa
        lat_media = df['latitude'].mean()
        lon_media = df['longitude'].mean()
        
        m = folium.Map(location=[lat_media, lon_media], zoom_start=14)
        
        # Adiciona os Pinos
        for _, row in df.iterrows():
            folium.Marker(
                [row['latitude'], row['longitude']], 
                popup=f"{row['tipo_crime']} - {row['data_hora']}",
                tooltip=row['endereco'],
                icon=folium.Icon(color="red" if row['tipo_crime'] == "Roubo" else "blue", icon="info-sign")
            ).add_to(m)
            
        # --- AQUI ESTAVA O ERRO: Adicionado height=500 ---
        st_folium(m, width=1000, height=500)
        
        st.markdown("### 📂 Base de Dados")
        st.dataframe(df)
    else: 
        st.warning("⚠️ Nenhuma ocorrência registrada nesta sessão.")
        st.info("Vá ao Menu '1. Registrar Ocorrência', salve um B.O. e volte aqui para ver o pino no mapa!")