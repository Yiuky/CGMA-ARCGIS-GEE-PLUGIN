# -*- coding: utf-8 -*-
"""
Python Toolbox (.pyt) para ArcGIS 10.8.2
Google Earth Engine Tools
"""

import os
import sys
import tempfile
import arcpy

# Adicionar pasta Install ao sys.path para carregar o gee_bridge
pyt_dir = os.path.dirname(os.path.abspath(__file__))
install_dir = os.path.join(pyt_dir, "..", "arcgis_addin", "Install")
if install_dir not in sys.path:
    sys.path.insert(0, install_dir)

try:
    import gee_bridge
except ImportError:
    gee_bridge = None

class Toolbox(object):
    def __init__(self):
        self.label = "Google Earth Engine Tools"
        self.alias = "geetools"
        self.tools = [AbrirInterfaceGEE, CarregarImagemGEE]

class AbrirInterfaceGEE(object):
    def __init__(self):
        self.label = "1. Abrir Painel Interativo GEE"
        self.description = "Abre a interface grafica completa com tabela de imagens, miniaturas e composicoes de bandas."
        self.canRunInBackground = False

    def getParameterInfo(self):
        return []

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        try:
            import gee_gui
            messages.addMessage("Abrindo painel interativo GEE...")
            gee_gui.open_gui()
        except Exception as e:
            messages.addErrorMessage("Erro ao abrir interface: " + str(e))

class CarregarImagemGEE(object):
    def __init__(self):
        self.label = "2. Baixar e Carregar Imagem/Mosaico GEE no TOC"
        self.description = "Filtra colecoes do GEE por satelite, data e regiao, e carrega diretamente no TOC."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 0. Satelite
        param_sensor = arcpy.Parameter(
            displayName="Satelite / Colecao",
            name="sensor",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_sensor.filter.type = "ValueList"
        param_sensor.filter.list = ["Sentinel-2", "Landsat 8", "Landsat 7", "Landsat 5"]
        param_sensor.value = "Sentinel-2"

        # 1. Composicao
        param_comp = arcpy.Parameter(
            displayName="Codigo da Composicao",
            name="composition",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_comp.value = "432"

        # 2. Data Inicio
        param_sdate = arcpy.Parameter(
            displayName="Data Inicial (AAAA-MM-DD)",
            name="start_date",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_sdate.value = "2024-01-01"

        # 3. Data Fim
        param_edate = arcpy.Parameter(
            displayName="Data Final (AAAA-MM-DD)",
            name="end_date",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_edate.value = "2024-02-01"

        # 4. Camada de Recorte / AOI (Opcional)
        param_aoi = arcpy.Parameter(
            displayName="Camada Vetorial de Recorte (AOI - Opcional)",
            name="aoi_layer",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input"
        )

        # 5. ID Especifico da Imagem (Opcional)
        param_img_id = arcpy.Parameter(
            displayName="ID Especifico da Imagem (Opcional)",
            name="image_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        # 6. Resolucao / Escala (metros)
        param_scale = arcpy.Parameter(
            displayName="Resolucao / Escala (metros)",
            name="scale",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        param_scale.value = 10

        return [param_sensor, param_comp, param_sdate, param_edate, param_aoi, param_img_id, param_scale]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if parameters[0].value == "Sentinel-2":
            parameters[6].value = 10
        else:
            parameters[6].value = 30
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        sensor_map = {
            "Sentinel-2": "S2",
            "Landsat 8": "L8",
            "Landsat 7": "L7",
            "Landsat 5": "L5"
        }
        sensor = sensor_map.get(str(parameters[0].value), "S2")
        comp = str(parameters[1].value).strip()
        sdate = str(parameters[2].value).strip()
        edate = str(parameters[3].value).strip()
        aoi_layer = parameters[4].valueAsText
        spec_id = parameters[5].valueAsText
        scale = int(parameters[6].value)

        messages.addMessage("Iniciando consulta ao Google Earth Engine...")

        bbox = None
        geojson_file = None
        if aoi_layer:
            tmp_geo = os.path.join(tempfile.gettempdir(), "pyt_gee_aoi.geojson")
            geojson_file = gee_bridge.export_layer_to_geojson(aoi_layer, tmp_geo)
        else:
            bbox = gee_bridge.get_arcmap_extent_wgs84()

        if spec_id:
            image_ids = [spec_id.strip()]
        else:
            # Buscar imagens
            messages.addMessage("Buscando imagens disponiveis no periodo...")
            s_res = gee_bridge.search_images(sensor, sdate, edate, bbox=bbox, geojson_file=geojson_file, max_images=10)
            if not s_res.get('success') or not s_res.get('images'):
                messages.addErrorMessage("Nenhuma imagem encontrada ou erro na busca: " + s_res.get('message', 'Sem resultados'))
                return
            image_ids = [img['id'] for img in s_res.get('images')[:1]]
            messages.addMessage("Imagem selecionada: " + image_ids[0])

        out_tif = os.path.join(tempfile.gettempdir(), "GEE_%s_%s_%s.tif" % (sensor, comp, sdate))
        messages.addMessage("Realizando download do GeoTIFF processado...")

        resp = gee_bridge.download_image(
            image_ids=image_ids,
            sensor=sensor,
            comp_code=comp,
            out_tif=out_tif,
            bbox=bbox,
            geojson_file=geojson_file,
            scale=scale
        )

        if resp.get('success'):
            tif_file = resp.get('file')
            messages.addMessage("Download concluido: " + tif_file)
            messages.addMessage("Carregando camada no TOC do ArcMap...")
            ok, msg = gee_bridge.load_into_toc(tif_file, layer_name="GEE_%s_%s" % (sensor, comp))
            if ok:
                messages.addMessage(msg)
            else:
                messages.addWarningMessage(msg)
        else:
            messages.addErrorMessage("Falha ao baixar imagem: " + resp.get('message', 'Erro desconhecido'))
