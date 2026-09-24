# CGMA ArcGIS GEE Plugin (v1.4)

[![ArcGIS](https://img.shields.io/badge/ArcGIS%20Desktop-10.8%20%7C%2010.8.2-blue.svg)](https://www.esri.com/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-API-green.svg)](https://earthengine.google.com/)
[![Python](https://img.shields.io/badge/Python-2.7%20%7C%203.9+-yellow.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Versão-v1.4%20Estável-brightgreen.svg)]()

Plugin avançado para o **ArcGIS Desktop 10.8 / 10.8.2 (ArcMap)** que integra diretamente a infraestrutura do **Google Earth Engine (GEE)** ao ambiente SIG da Esri. Permite pesquisar, filtrar, pré-visualizar e descarregar imagens de satélite (**Sentinel-2** e **Landsats 1 a 8**), índices espectrais e matemática de bandas diretamente na Tabela de Conteúdos (**TOC**) do ArcMap com **garantia estrita de 100% da resolução nativa** (sem reamostragem ou degradação de qualidade).

Desenvolvido para operações de geoprocessamento da **CGMA / SEMA-MT**.

---

## 🌟 Principais Recursos e Diferenciais

* **🎯 Garantia Estrita de Qualidade Nativa 100% (Novidade v1.4):**
  * **Zero degradação ou reamostragem:** O plugin garante que nenhum download sofra redução silenciosa de qualidade (preservando estritamente os 10m nativos no Sentinel-2 e os 30m no Landsat).
  * **Foco em Áreas Reais de Estudo:** Recorte espacial focado exclusivamente na **Extensão da Tela do ArcMap** e em **Camadas Vetoriais (AOI)** do TOC.
  * **Proteção Preventiva de Limite (48 MB GEE):** Se uma extensão ou camada vetorial selecionada demandar um volume superior ao teto de 48 MB do GEE na resolução nativa, o plugin **cancela o download e instrui o usuário** a aproximar o zoom (ex: <= 1:250.000 para Sentinel-2) ou refinar a AOI, eliminando qualquer risco de receber imagens com resolução rebaixada.
* **⚡ Arquitetura Assíncrona e Desacoplada (IPC Seguro):**
  * A interface gráfica opera em processo próprio (`pythonw.exe`), comunicando-se com o ArcMap via IPC estruturado (JSON com trava de reentrância atômica).
  * **Zero risco de travamento ou congelamento da UI do ArcMap** durante buscas ou downloads pesados.
* **🌱 Índices Espectrais e Matemática de Bandas Integrada:**
  * Cálculo em tempo real diretamente no Earth Engine de índices como **NDVI**, **NDWI**, **NDMI**, **NBR (Queimadas)**, **EVI** e **SAVI**.
  * **Fórmula Personalizada (Band Math):** Permite inserir expressões matemáticas customizadas (ex: `(B8-B4)/(B8+B4)` ou `(SR_B5-SR_B4)/(SR_B5+SR_B4)`), descarregando rasters Float32 monocamada com paleta de cores automática na miniatura e estatísticas calculadas no ArcMap.
* **📅 Entrada Flexível de Datas (Padrão Brasileiro DD/MM/AAAA):**
  * Campo de busca com suporte nativo a `DD/MM/AAAA` (ex: `15/08/2024`) bem como formato ISO `AAAA-MM-DD`.
* **🌈 Suporte Multibanda Completo (Preservação de Todas as Bandas):**
  * Baixa todas as bandas espectrais nativas (ex: 10 bandas no Sentinel-2, 7 bandas no Landsat 8/7/5) em um único arquivo GeoTIFF 32/16-bit.
  * Permite **alterar as bandas RGB diretamente no ArcMap TOC** em tempo real sem precisar refazer download.
* **📐 Resolução Espacial Customizável (Tamanho do Pixel em Metros):**
  * Campo dedicado para definir a resolução do raster exportado (ex: 10m para Sentinel-2, 20m para economia de memória, 30m para Landsat, ou qualquer valor personalizado).
* **🚀 Aceleração Multicore e Geoprocessamento Paralelo:**
  * Downloads simultâneos em segundo plano utilizando múltiplas threads/processos.
  * Cálculo paralelo de estatísticas e pirâmides no ArcPy (`parallelProcessingFactor`).
* **🎨 Painel de Configurações Avançadas de Realce (Stretch & Statistics):**
  * Janela modal dedicada para definir o Stretch padrão:
    * *Standard Deviations* (Desvio Padrão com `n` desvios configuráveis).
    * *DRA - Dynamic Range Adjustment* (*From Current Display Extent*).
    * *Percent Clip*, *Minimum-Maximum*, *Histogram Equalize*, etc.
* **📁 Agrupamento Inteligente no TOC:**
  * Inserção limpa dentro de camadas de grupo comuns (`GroupLayer`), evitando a criação de grupos de basemap que bloqueiam a troca de simbologia.
* **🖼️ Miniaturas Sob Demanda (Manuais):**
  * As miniaturas só são geradas quando o usuário clica no botão `[ Gerar Miniatura ]`, poupando tráfego de rede e acelerando a navegação na tabela.
* **🧩 Mosaicos Automáticos:**
  * Geração instantânea de mosaicos homogêneos (mediana temporal/espacial) a partir de múltiplas imagens selecionadas com recorte exato na Área de Interesse.

---

## 🏗️ Arquitetura do Sistema

```text
┌────────────────────────────────────────────────────────┐
│                   ArcMap 10.8 (Python 2.7)             │
│  - Toolbar "GEE Image Selector" (Python Add-In)       │
│  - ESRI ArcPy Engine (TOC, Data Frames, Simbologia)   │
│  - Win32 Native Timer IPC Listener (500ms)            │
└───────────────────────────▲────────────────────────────┘
                            │
              Arquivos de Comando JSON Atômicos
              (arcgis_gee_cmd.json / arcgis_gee_reply.json)
                            │
┌───────────────────────────▼────────────────────────────┐
│              Processo da GUI Independente              │
│  - Interface Tkinter / ttk (pythonw.exe)               │
│  - Validação de Escala (1:500.000) e Filtros           │
│  - Gerenciador de Tarefas em Segundo Plano             │
└───────────────────────────▲────────────────────────────┘
                            │ Subprocesso com pipes JSON
┌───────────────────────────▼────────────────────────────┐
│            Motor Backend GEE (Python 3.9+)             │
│  - earthengine-api (ee.ImageCollection, Reducers)     │
│  - Filtragem Espacial/Temporal e Mascaramento de Nuvens│
│  - Download de GeoTIFF Multibanda de Alta Performance │
└────────────────────────────────────────────────────────┘
```

---

## 💻 Requisitos do Sistema

1. **ArcGIS Desktop 10.8 ou 10.8.2** (ArcMap instalado).
2. **Python 2.7 do ArcGIS** (padrão em `C:\Python27\ArcGIS10.8\python.exe`).
3. **Python 3.9 ou superior** (pode ser o Python oficial, Anaconda, Miniconda ou o Python integrado do QGIS).
4. **Biblioteca Python do Google Earth Engine:**
   ```bash
   pip install earthengine-api
   ```
5. **Conta registrada no Google Earth Engine** com um Projeto no Google Cloud (ID do Projeto GEE).

---

## 📥 Instalação Rápida (Recomendado)

O repositório já inclui um script automatizado de instalação com 1 clique para configurar qualquer computador.

### Passo 1: Baixar ou Clonar o Repositório
```bash
git clone https://github.com/Yiuky/CGMA-ARCGIS-GEE-PLUGIN.git
cd CGMA-ARCGIS-GEE-PLUGIN
```
*(Ou baixe o arquivo ZIP pelo GitHub e extraia em qualquer pasta, ex: `C:\CGMA_ARCGIS_GEE_PLUGIN`)*.

### Passo 2: Executar o Instalador
1. Clique duas vezes no arquivo **`install.bat`**.
2. O instalador irá:
   * Detectar o ArcGIS 10.8 e o Python 2.7.
   * Localizar o Python 3 da máquina e instalar automaticamente a biblioteca `earthengine-api`.
   * Empacotar e registrar o Add-In `.esriaddin` na pasta oficial do ArcGIS Desktop.
   * Limpar caches residuais do ArcMap (`AssemblyCache`).
   * Disponibilizar a caixa de ferramentas `GEE_Tools.pyt`.

### Passo 3: Autenticar no Google Earth Engine (Apenas na 1ª vez)
1. Clique duas vezes no arquivo **`autenticar_gee.bat`** (ou use o botão *"Autenticar GEE"* dentro da interface do plugin).
2. O navegador será aberto para fazer login na conta Google e conceder acesso ao Earth Engine.

---

## 🛠️ Instalação Manual (Alternativa)

Se preferir instalar manualmente ou sem scripts:
1. Abra a pasta `arcgis_addin` e dê um duplo clique no arquivo **`GEE_Image_Selector.esriaddin`**.
2. Clique em **Install Add-In**.
3. No seu terminal Python 3, instale a API do GEE:
   ```bash
   pip install earthengine-api
   python -c "import ee; ee.Authenticate()"
   ```
4. Abra o ArcMap 10.8.

---

## 🚀 Como Utilizar no ArcMap

### 1. Ativar a Toolbar no ArcMap
1. Abra o **ArcMap 10.8**.
2. Vá ao menu superior: **Customize** > **Toolbars** e marque **`GEE Image Selector`**.
3. Clique no botão com o ícone do satélite **Seletor GEE**.

### 2. Configurar o Projeto GEE
1. No topo da interface, se o status estiver em amarelo/vermelho, clique em **Configurar Projeto GEE**.
2. Digite o ID do seu projeto Google Cloud associado ao GEE (ex: `ee-meuprojeto` ou `meu-projeto-12345`).
3. O status mudará para verde: `[OK] Conectado ao Google Earth Engine!`.

### 3. Definir Filtros e Parâmetros
1. **Satélite / Sensor:** Escolha Sentinel-2, Landsat 8, 7, 5, etc.
2. **Composição / Bandas:** Escolha entre as composições prontas (Cor Natural, Infravermelho, Falsa Cor, SWIR, etc.) ou selecione *Composição Customizada* para escolher bandas manualmente.
3. **Período e Nuvens:** Defina a data inicial, data final e porcentagem máxima de cobertura de nuvens.
4. **Área de Interesse (Filtro Espacial - Resolução Nativa 100%):**
   * *Extensão da Tela do ArcMap:* Usa automaticamente a visualização corrente do mapa (com validação de escala <= 1:500.000 e checagem preventiva de tamanho).
   * *Camada Vetorial (AOI):* Selecione qualquer camada vetorial (Shapefile ou Feature Class) presente no TOC do ArcMap para recortar e descarregar exatamente a geometria do seu polígono de estudo.
5. **Tamanho do Pixel (m):** Ajuste a resolução espacial desejada (padrão nativo: 10m para Sentinel-2, 30m para Landsat).
6. **Configurações de Stretch e Multicore:** Clique em **`[ Configurações ]`** para personalizar o número de cores da CPU e o tipo de realce de contraste (*Standard Deviation*, *Dynamic Range Adjustment*, etc.).

### 4. Buscar e Carregar Cenas
1. Clique em **Buscar Imagens no GEE**.
2. A lista de imagens encontradas será exibida na tabela com data, porcentagem de nuvens e identificação do tile.
3. **Miniatura:** Se desejar inspecionar a cena antes do download, selecione a linha desejada e clique em **`[ Gerar Miniatura ]`**.
4. **Carregamento:**
   * **`[ Carregar ]`**: Baixa a cena selecionada e insere diretamente no TOC dentro do grupo especificado, configurando automaticamente a simbologia RGB com as bandas corretas.
   * **`[ Carregar Todas ]`**: Baixa todas as cenas filtradas em paralelo utilizando aceleração Multicore.
   * **`[ Criar Mosaico ]`**: Gera um mosaico único homogêneo (mediana) combinando todas as imagens selecionadas.
   * **`[ Substituir no TOC ]`**: Substitui uma camada já existente na tela pela nova imagem mantendo a ordem exata das camadas.

---

## 🗂️ Estrutura do Repositório

```text
CGMA-ARCGIS-GEE-PLUGIN/
├── arcgis_addin/
│   ├── config.xml                      # Metadados do Add-In (versão, toolbar, comandos)
│   ├── makeaddin.py                    # Script de empacotamento do .esriaddin
│   ├── GEE_Image_Selector.esriaddin    # Pacote compilado instalável
│   ├── Images/
│   │   └── icon.png                    # Ícone oficial da Toolbar
│   └── Install/
│       ├── gee_selector_addin.py       # Ponto de entrada COM do ArcMap
│       ├── gee_gui.py                  # Interface gráfica desacoplada (Tkinter/ttk)
│       ├── gee_bridge.py               # Ponte IPC, controle de TOC e ArcPy
│       ├── empty_group_template.lyr    # Template puro de GroupLayer
│       └── backend/                    # Backend autocontido no pacote Add-in
│           ├── gee_core.py
│           ├── run_gee.py
│           └── gee_config.json
├── backend/
│   ├── gee_core.py                     # Motor principal do GEE, coleções e GeoTIFF
│   ├── run_gee.py                      # Linha de comando para comunicação JSON
│   └── gee_config.json                 # Configuração persistente do projeto GEE
├── pyt/
│   └── GEE_Tools.pyt                   # Caixa de ferramentas Python para ArcToolbox
├── install.bat                         # Instalador automatizado para Windows
├── autenticar_gee.bat                  # Utilitário de autenticação GEE
├── requirements.txt                    # Dependências do Python 3
├── .gitignore                          # Arquivos ignorados pelo controle de versão
└── README.md                           # Documentação completa
```

---

## ❓ Perguntas Frequentes e Solução de Problemas

### 1. "Aviso: A escala atual do ArcMap é maior que 1:500.000"
* **Motivo:** O Google Earth Engine possui limites de requisição por recorte para evitar sobrecarga. Escalas muito distantes cobrem áreas imensas.
* **Solução:** Dê zoom em sua área de estudo até que a escala esteja abaixo de 1:500.000 (ex: 1:250.000 ou 1:100.000) ou clique no botão **`[ Ajustar 1:500.000 ]`** na barra superior da interface.

### 2. "Erro ao adicionar camada ao TOC: maximum recursion depth exceeded"
* **Status:** **Totalmente corrigido**.
* A biblioteca `gee_bridge.py` agora conta com guarda estrita contra reentrância (`_is_processing_cmd`) e exclusão atômica e imediata dos arquivos de comando IPC.

### 3. As bandas na Tabela de Conteúdos não mostram todas as bandas
* **Status:** O plugin exporta e carrega o GeoTIFF completo contendo todas as bandas nativas (`Band_1`, `Band_2`, `Band_3`, `Band_4`, ..., `Band_10`).
* Para alterar a combinação exibida, você pode usar o botão **`[ Aplicar Composição ]`** na interface ou abrir as propriedades da camada no ArcMap (*Layer Properties > Symbology > Red / Green / Blue*).

### 4. Como trocar o ambiente Python 3 usado pelo Plugin?
* O plugin detecta automaticamente o Python 3 nas pastas padrão ou no QGIS.
* Caso queira fixar um interpretador específico, defina a variável de ambiente do Windows `GEE_PYTHON3`:
  ```cmd
  setx GEE_PYTHON3 "C:\Caminho\Para\Seu\Python3\python.exe"
  ```

### 5. "Qualidade Nativa Estrita (Limite Excedido): A extensão atual da tela requer aproximadamente X MB (limite: 48 MB)"
* **Motivo:** O endpoint de download direto do Google Earth Engine possui um teto de 48 MB por requisição. Anteriormente, softwares de terceiros reamostravam a imagem silenciosamente (ex: de 10m para 40m ou 80m), degradando a resolução do raster.
* **Comportamento v1.4:** **Zero perda de qualidade!** O plugin recusa-se a degradar os dados do usuário. Se a área na resolução nativa (10m Sentinel-2 / 30m Landsat) for maior que 48 MB, ele cancela o download preventivamente e avisa o usuário.
* **Solução:** Aumente o zoom no ArcMap para uma escala mais próxima (ex: <= 1:250.000 para Sentinel-2 ou selecione uma composição com menos bandas) ou utilize um Shapefile/Feature Class de AOI como filtro espacial.

---

## 👤 Autor e Licença

* **Autor:** Joberth Firmino Gambati
* **GitHub:** [@Yiuky](https://github.com/Yiuky)
* **Organização:** Coordenadoria de Geoprocessamento e Monitoramento Ambiental (CGMA) / SEMA-MT
* **Licença:** Distribuído sob a licença [MIT](LICENSE). Uso livre para fins institucionais, acadêmicos e comerciais.
