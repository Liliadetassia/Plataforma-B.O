# Sistema Integrado de Inteligência Policial (MVP)

Uma plataforma mvp de segurança pública desenvolvida em Python, integrando reconhecimento de placas (LPR), geolocalização de ocorrências e comunicação automática via WhatsApp.

## 🚀 Funcionalidades

O sistema é dividido em 3 módulos operacionais:

### 1. 📝 Registro de Ocorrência (B.O. Fácil)
- **Geolocalização Automática:** Validação de endereços usando API Nominatim (OpenStreetMap).
- **Geração de Documentos:** Criação automática de Boletim de Ocorrência (B.O.) em PDF oficial.
- **Notificação via WhatsApp:** Envio do PDF e resumo da ocorrência para o solicitante via Evolution API.
- **Armazenamento:** Salva dados temporários em memória para análise.

### 2. 📷 Reconhecimento de Placas (LPR - License Plate Recognition)
- **Visão Computacional:** Utiliza `EasyOCR` e `OpenCV` para leitura de placas em fotos.
- **Tratamento de Imagem:** Algoritmos de pré-processamento (Zoom, Contraste CLAHE) para ler placas em condições difíceis.
- **Inteligência Lógica:** Correção automática de erros comuns de OCR (Ex: confundir '8' com 'B', '1' com 'I').
- **Simulação de Base de Dados:** Verifica se o veículo é roubado/furtado ou regular (Simulação DETRAN/SINESP).

### 3. 📊 Sala de Situação (Inteligência Geospacial)
- **Mapa de Calor (Heatmap):** Visualização interativa de todas as ocorrências registradas na sessão.
- **Dashboard:** Métricas em tempo real e tabela de dados.

## 🛠️ Tecnologias Utilizadas

- **Frontend/Backend:**
  
- **Visão Computacional:**
  
- **Mapas e Geolocalização:**
  
- **Geração de Arquivos:**
  
- **Integração WhatsApp:** 


## ⚙️ Pré-requisitos

- Python 3.9 ou superior
- Conta/Instância configurada na Evolution API (para envio de WhatsApp)

## Observação:

Em testes que realizei não tive muito êxito no reconhecimento de placa usando a biblioteca EasyOCR. O ideal seria usar também a Tesseract, porém não trabalhei mais afundo no projeto nessa parte, podendo ser explorado melhor para êxito.
