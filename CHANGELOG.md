# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato baseia-se no [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto segue o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.6.0] - 2026-09-25

### 🌟 Adicionado
- **Download Inteligente de Áreas Extensas (> 48 MB) com Particionamento Espacial (*Smart Spatial Tiling*):**
  - Permite o download de imagens e mosaicos cobrindo grandes extensões territoriais em escalas de até **1:500.000** sem bloqueio ou cancelamento pela cota de 48 MB do Google Earth Engine.
  - **Garantia Estrita de Qualidade Nativa 100%:** Elimina qualquer necessidade de reamostragem, preservando estritamente os 10 metros nativos no Sentinel-2 e os 30 metros no Landsat em toda a extensão do mapa.
  - **Grade Espacial Automatizada ($N_x \times N_y$):** O backend calcula a partição ótima de quadrantes baseada no número de bandas e resolução solicitada, mantendo cada requisição individual abaixo de 32 MB (com margem de segurança contra o teto de 48 MB).
  - **Micro-Sobreposição (*Overlap*) de Bordas:** Adição de margem de 1.5 pixels entre quadrantes internos adjacentes para garantir zero costuras, frestas ou artefatos de arredondamento cartográfico.
  - **Download Paralelo Multithread:** Os quadrantes da grade são baixados simultaneamente em segundo plano utilizando `concurrent.futures.ThreadPoolExecutor`, maximizando a velocidade de transferência.
  - **Mosaico Automatizado com GDAL:** Motor de fusão inteligente multi-plataforma que mescla os quadrantes em um único GeoTIFF contínuo georreferenciado com compressão LZW, estrutura interna em blocos (`TILED=YES`) e suporte a BigTIFF (`BIGTIFF=IF_SAFER`).
  - **Detecção e Descarte de Quadrantes Vazios na AOI:** Para camadas vetoriais irregulares, quadrantes que não interceptam o polígono de interesse são ignorados automaticamente, economizando banda e tempo de processamento.
  - **Feedback Visual Dinâmico:** A barra de status e o diálogo de progresso informam em tempo real a estimativa de tamanho em megabytes e a quantidade de quadrantes sendo baixados e mesclados.

### 🔄 Modificado
- **Priorização de Interpretadores Python com GDAL Nativo:** A busca por interpretadores Python 3 agora prioriza ambientes com suporte simultâneo à Earth Engine API e à biblioteca `osgeo.gdal` nativa (como o Python do QGIS 3.x), com fallback automático para subprocessos e CLI.
- **Atualização do Limite de Escala na Interface:** As mensagens e dicas da interface agora confirmam o suporte pleno a downloads de áreas de trabalho em escalas de até 1:500.000 em resolução nativa.

### 🛡️ Corrigido
- **Correção de Atribuição da Variável `is_multi`:** Resolução de erro em execuções no modo de carga rápida RGB (`load_mode='rgb'`), garantindo compatibilidade uniforme em todos os modos de exportação.

---

## [1.5.0] - 2026-09-24

### 🌟 Adicionado
- **Metadados de Período Operacional dos Sensores:** Exibição dinâmica do intervalo temporal de dados e do status de operação de cada satélite/sensor selecionado (Sentinel-2 MSI, Landsat 8/9 OLI, Landsat 7 ETM+, Landsat 4-5 TM, Landsat 1-5 MSS).
- **Verificação Automática de Atualização na Inicialização:** Rotina assíncrona em segundo plano que consulta o GitHub para verificar a existência de novas versões do plugin sem congelar a interface.
- **Bypass de Cache CDN do GitHub:** Requisições de checagem com cabeçalhos anti-cache (`Cache-Control: no-cache, no-store`) e parâmetro aleatório de timestamp para garantir que o cliente receba a versão mais recente em tempo real.
- **Notificação Não-Intrusiva na UI:** Indicação sutil na barra de status informando quando há uma nova versão disponível, com acesso direto ao atualizador integrado.

### 🔄 Modificado
- **Otimização de SEO e Rebranding do Repositório:** O repositório oficial no GitHub foi renomeado para `arcgis-google-earth-engine-explorer`, maximizando a relevância e indexação em mecanismos de busca (Google, Bing e GitHub Search).
- **Evolução do Mecanismo de Deploy:** O script de implantação foi aprimorado para validar a compatibilidade de bytecode entre diferentes revisões do ArcGIS 10.8 e 10.8.2.

### 🛡️ Corrigido
- **Correção de Sintaxe no Bloco de Checagem (Python 2.7):** Resolução de um erro de indentação e omissão de bloco condicional que causava encerramento silencioso do processo `pythonw.exe`.
- **Purga Atômica de Bytecode (`.pyc`) no AssemblyCache:** Eliminação de arquivos de bytecode antigos e corrompidos na pasta de cache do ArcGIS durante o processo de atualização via ZIP ou Git, impedindo que o ArcMap execute códigos compilados obsoletos.
- **Isolamento de Arquivos no Instalador:** Prevenção contra extração acidental de arquivos de raiz do repositório (`.gitignore`, `README.md`) para dentro do diretório de montagem de extensões do ArcGIS.

---

## [1.4.2] - 2026-09-24

### 🌟 Adicionado
- **Nova Identidade Visual Oficial (Ícone 3D):** Criação e integração do logotipo moderno do satélite em múltiplos formatos e resoluções (`16x16`, `20x20`, `24x24`, `32x32`, `48x48`, `64x64`, `.ico` e `.png`).
- **Botão Oficial com Ícone e Texto no ArcMap:** Barra de ferramentas configurada para exibir o rótulo **ArcGEE Explorer** acompanhado do ícone temático.
- **Exibição do Logotipo em Alta Resolução:** Janela "Sobre" enriquecida com o emblema oficial do satélite e identificação visual da CGMA / SEMA-MT.

### 🔄 Modificado
- **Padronização de Nomenclatura:** Atualização do nome oficial da aplicação em toda a interface e documentação para **CGMA ArcGEE Explorer**.
- **Simplificação da Barra Superior:** Remoção do botão redundante de stretch no topo da janela, consolidando todas as configurações de realce radiométrico dentro do painel de preferências avançadas.

---

## [1.4.1] - 2026-09-24

### 🌟 Adicionado
- **Assistente Integrado de Atualizações (Dual-Mode Updater):**
  - *Método 1 (Online):* Download direto e atualização automática em 1 clique a partir da branch principal do GitHub.
  - *Método 2 (Offline / Manual):* Atualização a partir de arquivo `.zip` baixado manualmente pelo usuário.
- **Janela Modal "Sobre" (About Dialog):** Informações detalhadas da versão, arquitetura, licença MIT, créditos de desenvolvimento e atalhos rápidos.
- **Buffer Envolvente Configurável para Camada Vetorial (AOI):** Adição de margem de segurança configurável (padrão de 1.000 metros) ao redor de polígonos de estudo para garantir cobertura completa de bordas.
- **Scripts Auxiliares de Manutenção:** Inclusão dos scripts `desinstalar.bat` (limpeza completa de Add-In e caches) e `atualizar.bat` (atualizador via terminal).

### 🛡️ Corrigido
- **Compatibilidade do Descompactador ZIP no Python 2.7:** Substituição da chamada `ZipInfo.is_dir()` (incompatível com Python 2.7) por validação de terminação de diretório (`name.endswith('/')`).
- **Sanitização de Geometria GeoJSON para AOI:** Reprojeção prévia para WGS84 (EPSG:4326) e correção de polígonos complexos, eliminando a mensagem de erro `"Invalid GeoJSON geometry"`.

---

## [1.4.0] - 2026-09-23

### 🌟 Adicionado
- **Garantia Estrita de Qualidade Nativa 100%:**
  - Proibição de reamostragem silenciosa: preserva estritamente os 10 metros nativos no Sentinel-2 e os 30 metros no Landsat.
  - Eliminação de qualquer risco de degradação de dados espectrais ou espaciais.
- **Checagem Preventiva do Limite do Earth Engine (48 MB):**
  - Estimativa do tamanho da cena antes do download com base no número de bandas e tamanho do pixel.
  - Bloqueio preventivo caso a requisição exceda o teto de download da API do GEE, fornecendo instruções claras ao usuário para ajustar o zoom (escala <= 1:250.000) ou refinar a AOI.
- **Painel de Configurações Avançadas de Realce (Stretch & Statistics):**
  - Controle completo sobre o método de stretch padrão no ArcMap: *Standard Deviations* (`n` desvios configuráveis), *Dynamic Range Adjustment (DRA)*, *Percent Clip*, *Minimum-Maximum* e *Histogram Equalization*.
- **Agrupamento Puro no TOC (`GroupLayer`):** Inserção de imagens dentro de camadas de grupo convencionais do ArcMap, evitando o bloqueio de simbologia característico de basemaps compostos.

### 🔄 Modificado
- **Remoção do Modo "Cena Completa":** Substituído pelo foco estrito na extensão de tela e em polígonos vetoriais, otimizando o consumo de banda e garantindo alta performance.

---

## [1.3.0] - 2026-09-23

### 🌟 Adicionado
- **Cálculo de Índices Espectrais no Earth Engine:** Suporte nativo para geração direta de rasters Float32 monocamada:
  - **NDVI** (Índice de Vegetação por Diferença Normalizada)
  - **NDWI** (Índice de Água por Diferença Normalizada)
  - **NDMI** (Índice de Umidade por Diferença Normalizada)
  - **NBR** (Razão de Queima Normalizada / Detecção de Incêndios)
  - **EVI** (Índice de Vegetação Melhorado)
  - **SAVI** (Índice de Vegetação Ajustado ao Solo)
- **Matemática de Bandas Personalizada (Custom Band Math):** Permite ao operador inserir expressões matemáticas arbitrárias (ex: `(B8-B4)/(B8+B4)` ou `(SR_B5-SR_B4)/(SR_B5+SR_B4)`).
- **Modo Multibanda Bruta Completa:** Exporta todas as bandas espectrais nativas em um único GeoTIFF, permitindo ao usuário alterar a composição RGB diretamente nas propriedades da camada no TOC sem necessidade de refazer o download.
- **Suporte a Datas no Formato Brasileiro:** Campos de pesquisa com suporte nativo a `DD/MM/AAAA` (ex: `15/08/2024`) com validação automática e conversão para o padrão ISO `AAAA-MM-DD`.

### 🔄 Modificado
- **Busca Orbital Global:** Remoção do filtro espacial restrito ao território de Mato Grosso, permitindo buscas em qualquer localidade do planeta.

---

## [1.2.0] - 2026-09-23

### 🌟 Adicionado
- **Geração de Mosaicos Automáticos (Mediana Temporal):** Criação de mosaicos homogêneos e livres de nuvens a partir de múltiplas imagens selecionadas na grade de resultados.
- **Filtro Espacial por Camada Vetorial (AOI):** Seleção de qualquer camada vetorial (Shapefile ou Feature Class) ativa na Tabela de Conteúdos do ArcMap.
- **Seletor de Resolução Espacial Customizável:** Campo dedicado para definir o tamanho do pixel em metros (ex: 10m, 20m, 30m ou valores arbitrários).
- **Aceleração Multicore em Segundo Plano:** Processamento paralelo de múltiplos downloads simultâneos e cálculo paralelo de pirâmides e estatísticas no ArcPy (`parallelProcessingFactor`).
- **Caixa de Ferramentas Python Toolbox (`GEE_Tools.pyt`):** Disponibilização de ferramentas de geoprocessamento integradas ao ArcToolbox para workflows automatizados em ModelBuilder e scripts de linha de comando.

---

## [1.0.0] - 2026-09-23

### 🌟 Lançamento Inicial
- Arquitetura desacoplada e assíncrona via IPC estruturado (arquivos de comando JSON com bloqueio atômico) conectando o ArcMap 10.8 (Python 2.7) ao motor de geoprocessamento (Python 3.9+ e `earthengine-api`).
- Interface gráfica moderna e responsiva construída em Tkinter/ttk.
- Suporte inicial a coleções de dados Sentinel-2 (TOA/SR Harmonized) e Landsat 1 a 9 (MSS, TM, ETM+, OLI/TIRS).
- Filtros por satélite, período de datas, porcentagem máxima de cobertura de nuvens e escala visual.
- Sistema de miniaturas sob demanda (*On-Demand Thumbnails*) para inspeção rápida de cenas sem consumo excessivo de tráfego de dados.
- Configuração e autenticação persistente com projetos no Google Earth Engine.
