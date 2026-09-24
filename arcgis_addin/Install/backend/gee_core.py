# -*- coding: utf-8 -*-
"""
Motor de Processamento Google Earth Engine (Python 3)
Compatível com earthengine-api.
Baseado no script de seleção e mosaico GEE para Mato Grosso / Brasil.
"""

import os
import sys
import json
import urllib.request
import tempfile
import ee

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gee_config.json")

COLLECTIONS = {
    'S2': 'COPERNICUS/S2_SR_HARMONIZED',
    'L8': 'LANDSAT/LC08/C02/T1_L2',
    'L7': 'LANDSAT/LE07/C02/T1_L2',
    'L5': 'LANDSAT/LT05/C02/T1_L2',
    'L4': 'LANDSAT/LT04/C02/T1_L2',
    'L3': 'LANDSAT/LM03/C01/T1',
    'L2': 'LANDSAT/LM02/C01/T2',
    'L1': 'LANDSAT/LM01/C01/T2'
}

MULTIBAND_DEFAULT_BANDS = {
    'S2': ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12'],
    'L8': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'],
    'L7': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'],
    'L5': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'],
    'L4': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'],
    'L3': ['B4', 'B5', 'B6', 'B7'],
    'L2': ['B4', 'B5', 'B6', 'B7'],
    'L1': ['B4', 'B5', 'B6', 'B7']
}

def get_image_collection(sensor):
    """Retorna colecao de imagens incluindo Tier 1 e Tier 2 para Landsat para garantir busca de todas as datas"""
    if sensor == 'S2':
        return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    elif sensor == 'L8':
        t1 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        t2 = ee.ImageCollection('LANDSAT/LC08/C02/T2_L2')
        l9_t1 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        l9_t2 = ee.ImageCollection('LANDSAT/LC09/C02/T2_L2')
        return t1.merge(t2).merge(l9_t1).merge(l9_t2)
    elif sensor == 'L7':
        t1 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
        t2 = ee.ImageCollection('LANDSAT/LE07/C02/T2_L2')
        return t1.merge(t2)
    elif sensor == 'L5':
        t1 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
        t2 = ee.ImageCollection('LANDSAT/LT05/C02/T2_L2')
        return t1.merge(t2)
    elif sensor == 'L4':
        t1 = ee.ImageCollection('LANDSAT/LT04/C02/T1_L2')
        t2 = ee.ImageCollection('LANDSAT/LT04/C02/T2_L2')
        return t1.merge(t2)
    elif sensor in ['L1', 'L2', 'L3']:
        c = COLLECTIONS.get(sensor, 'LANDSAT/LM01/C01/T2')
        return ee.ImageCollection(c)
    else:
        return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')

COMPOSITIONS = {
    'L8': {
        '432': {'label': 'COR NATURAL - 432', 'bands': ['SR_B4', 'SR_B3', 'SR_B2']},
        '764': {'label': 'FALSA COR - 764', 'bands': ['SR_B7', 'SR_B6', 'SR_B4']},
        '543': {'label': 'COR INFRAVERMELHA (VEGETACAO) - 543', 'bands': ['SR_B5', 'SR_B4', 'SR_B3']},
        '652': {'label': 'AGRICULTURA - 652', 'bands': ['SR_B6', 'SR_B5', 'SR_B2']},
        '765': {'label': 'PENETRACAO ATMOSFERICA - 765', 'bands': ['SR_B7', 'SR_B6', 'SR_B5']},
        '562': {'label': 'SAUDE DA VEGETACAO - 562', 'bands': ['SR_B5', 'SR_B6', 'SR_B2']},
        '564': {'label': 'SOLO/AGUA - 564', 'bands': ['SR_B5', 'SR_B6', 'SR_B4']},
        '753': {'label': 'NATURAL COM REMOCAO ATMOSFERICA - 753', 'bands': ['SR_B7', 'SR_B5', 'SR_B3']},
        '754': {'label': 'INFRAVERMELHO ONDA CURTA - 754', 'bands': ['SR_B7', 'SR_B5', 'SR_B4']},
        '654': {'label': 'ANALISE DA VEGETACAO - 654', 'bands': ['SR_B6', 'SR_B5', 'SR_B4']},
        'MB_7': {'label': 'MULTIBANDA - 7 BANDAS (SR_B1 a SR_B7)', 'bands': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'], 'multiband': True},
        'MB_6': {'label': 'MULTIBANDA - 6 BANDAS (SR_B2 a SR_B7)', 'bands': ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'], 'multiband': True},
        'NDVI': {'label': 'INDICE - NDVI (Vegetacao: NIR-RED)', 'bands': ['SR_B5', 'SR_B4'], 'is_index': True},
        'NDWI': {'label': 'INDICE - NDWI (Agua: GREEN-NIR)', 'bands': ['SR_B3', 'SR_B5'], 'is_index': True},
        'NDMI': {'label': 'INDICE - NDMI (Umidade: NIR-SWIR1)', 'bands': ['SR_B5', 'SR_B6'], 'is_index': True},
        'NBR':  {'label': 'INDICE - NBR (Queimadas: NIR-SWIR2)', 'bands': ['SR_B5', 'SR_B7'], 'is_index': True},
        'EVI':  {'label': 'INDICE - EVI (Vegetacao Realcada)', 'bands': ['SR_B5', 'SR_B4', 'SR_B2'], 'is_index': True},
        'SAVI': {'label': 'INDICE - SAVI (Ajustado ao Solo)', 'bands': ['SR_B5', 'SR_B4'], 'is_index': True},
        'CUSTOM_MATH': {'label': 'INDICE - FORMULA PERSONALIZADA...', 'bands': [], 'is_index': True, 'is_custom': True}
    },
    'L7': {
        '321': {'label': 'COR NATURAL - 321', 'bands': ['SR_B3', 'SR_B2', 'SR_B1']},
        '753': {'label': 'FALSA COR - 753', 'bands': ['SR_B7', 'SR_B5', 'SR_B3']},
        '432': {'label': 'COR INFRAVERMELHA (VEGETACAO) - 432', 'bands': ['SR_B4', 'SR_B3', 'SR_B2']},
        '541': {'label': 'AGRICULTURA - 541', 'bands': ['SR_B5', 'SR_B4', 'SR_B1']},
        '754': {'label': 'PENETRACAO ATMOSFERICA - 754', 'bands': ['SR_B7', 'SR_B5', 'SR_B4']},
        '451': {'label': 'SAUDE DA VEGETACAO - 451', 'bands': ['SR_B4', 'SR_B5', 'SR_B1']},
        '453': {'label': 'SOLO/AGUA - 453', 'bands': ['SR_B4', 'SR_B5', 'SR_B3']},
        '742': {'label': 'NATURAL COM REMOCAO ATMOSFERICA - 742', 'bands': ['SR_B7', 'SR_B4', 'SR_B2']},
        '743': {'label': 'INFRAVERMELHO ONDA CURTA - 743', 'bands': ['SR_B7', 'SR_B4', 'SR_B3']},
        '543': {'label': 'ANALISE DA VEGETACAO - 543', 'bands': ['SR_B5', 'SR_B4', 'SR_B3']},
        'MB_6': {'label': 'MULTIBANDA - 6 BANDAS (SR_B1 a SR_B5, SR_B7)', 'bands': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'], 'multiband': True},
        'NDVI': {'label': 'INDICE - NDVI (Vegetacao: NIR-RED)', 'bands': ['SR_B4', 'SR_B3'], 'is_index': True},
        'NDWI': {'label': 'INDICE - NDWI (Agua: GREEN-NIR)', 'bands': ['SR_B2', 'SR_B4'], 'is_index': True},
        'NDMI': {'label': 'INDICE - NDMI (Umidade: NIR-SWIR1)', 'bands': ['SR_B4', 'SR_B5'], 'is_index': True},
        'NBR':  {'label': 'INDICE - NBR (Queimadas: NIR-SWIR2)', 'bands': ['SR_B4', 'SR_B7'], 'is_index': True},
        'EVI':  {'label': 'INDICE - EVI (Vegetacao Realcada)', 'bands': ['SR_B4', 'SR_B3', 'SR_B1'], 'is_index': True},
        'SAVI': {'label': 'INDICE - SAVI (Ajustado ao Solo)', 'bands': ['SR_B4', 'SR_B3'], 'is_index': True},
        'CUSTOM_MATH': {'label': 'INDICE - FORMULA PERSONALIZADA...', 'bands': [], 'is_index': True, 'is_custom': True}
    },
    'L5': {
        '321': {'label': 'COR NATURAL - 321', 'bands': ['SR_B3', 'SR_B2', 'SR_B1']},
        '753': {'label': 'FALSA COR - 753', 'bands': ['SR_B7', 'SR_B5', 'SR_B3']},
        '432': {'label': 'COR INFRAVERMELHA (VEGETACAO) - 432', 'bands': ['SR_B4', 'SR_B3', 'SR_B2']},
        '541': {'label': 'AGRICULTURA - 541', 'bands': ['SR_B5', 'SR_B4', 'SR_B1']},
        '754': {'label': 'PENETRACAO ATMOSFERICA - 754', 'bands': ['SR_B7', 'SR_B5', 'SR_B4']},
        '451': {'label': 'SAUDE DA VEGETACAO - 451', 'bands': ['SR_B4', 'SR_B5', 'SR_B1']},
        '453': {'label': 'SOLO/AGUA - 453', 'bands': ['SR_B4', 'SR_B5', 'SR_B3']},
        '742': {'label': 'NATURAL COM REMOCAO ATMOSFERICA - 742', 'bands': ['SR_B7', 'SR_B4', 'SR_B2']},
        '743': {'label': 'INFRAVERMELHO ONDA CURTA - 743', 'bands': ['SR_B7', 'SR_B4', 'SR_B3']},
        '543': {'label': 'ANALISE DA VEGETACAO - 543', 'bands': ['SR_B5', 'SR_B4', 'SR_B3']},
        'MB_6': {'label': 'MULTIBANDA - 6 BANDAS (SR_B1 a SR_B5, SR_B7)', 'bands': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'], 'multiband': True},
        'NDVI': {'label': 'INDICE - NDVI (Vegetacao: NIR-RED)', 'bands': ['SR_B4', 'SR_B3'], 'is_index': True},
        'NDWI': {'label': 'INDICE - NDWI (Agua: GREEN-NIR)', 'bands': ['SR_B2', 'SR_B4'], 'is_index': True},
        'NDMI': {'label': 'INDICE - NDMI (Umidade: NIR-SWIR1)', 'bands': ['SR_B4', 'SR_B5'], 'is_index': True},
        'NBR':  {'label': 'INDICE - NBR (Queimadas: NIR-SWIR2)', 'bands': ['SR_B4', 'SR_B7'], 'is_index': True},
        'EVI':  {'label': 'INDICE - EVI (Vegetacao Realcada)', 'bands': ['SR_B4', 'SR_B3', 'SR_B1'], 'is_index': True},
        'SAVI': {'label': 'INDICE - SAVI (Ajustado ao Solo)', 'bands': ['SR_B4', 'SR_B3'], 'is_index': True},
        'CUSTOM_MATH': {'label': 'INDICE - FORMULA PERSONALIZADA...', 'bands': [], 'is_index': True, 'is_custom': True}
    },
    'L1': {
        '321': {'label': 'COR NATURAL - 321', 'bands': ['SR_B3', 'SR_B2', 'SR_B1']},
        '753': {'label': 'FALSA COR - 753', 'bands': ['SR_B7', 'SR_B5', 'SR_B3']},
        '432': {'label': 'COR INFRAVERMELHA (VEGETACAO) - 432', 'bands': ['SR_B4', 'SR_B3', 'SR_B2']},
        '541': {'label': 'AGRICULTURA - 541', 'bands': ['SR_B5', 'SR_B4', 'SR_B1']},
        '754': {'label': 'PENETRACAO ATMOSFERICA - 754', 'bands': ['SR_B7', 'SR_B5', 'SR_B4']},
        '451': {'label': 'SAUDE DA VEGETACAO - 451', 'bands': ['SR_B4', 'SR_B5', 'SR_B1']},
        '453': {'label': 'SOLO/AGUA - 453', 'bands': ['SR_B4', 'SR_B5', 'SR_B3']},
        '742': {'label': 'NATURAL COM REMOCAO ATMOSFERICA - 742', 'bands': ['SR_B7', 'SR_B4', 'SR_B2']},
        '743': {'label': 'INFRAVERMELHO ONDA CURTA - 743', 'bands': ['SR_B7', 'SR_B4', 'SR_B3']},
        '654': {'label': 'ANALISE DA VEGETACAO - 654', 'bands': ['SR_B6', 'SR_B5', 'SR_B4']},
        'NDVI': {'label': 'INDICE - NDVI (Vegetacao: NIR-RED)', 'bands': ['B7', 'B5'], 'is_index': True},
        'NDWI': {'label': 'INDICE - NDWI (Agua: GREEN-NIR)', 'bands': ['B4', 'B7'], 'is_index': True},
        'CUSTOM_MATH': {'label': 'INDICE - FORMULA PERSONALIZADA...', 'bands': [], 'is_index': True, 'is_custom': True}
    },
    'S2': {
        '432': {'label': 'COR NATURAL - 4.3.2', 'bands': ['B4', 'B3', 'B2']},
        '12114': {'label': 'FALSA COR - 12.11.4', 'bands': ['B12', 'B11', 'B4']},
        '843': {'label': 'COR INFRAVERMELHA (VEGETACAO) - 8.4.3', 'bands': ['B8', 'B4', 'B3']},
        '8a43': {'label': 'COR INFRAVERMELHA (VEGETACAO) - 8a.4.3', 'bands': ['B8A', 'B4', 'B3']},
        '1182': {'label': 'AGRICULTURA - 11.8.2', 'bands': ['B11', 'B8', 'B2']},
        '118a2': {'label': 'AGRICULTURA - 11.8a.2', 'bands': ['B11', 'B8A', 'B2']},
        '12118': {'label': 'PENETRACAO ATMOSFERICA - 12.11.8', 'bands': ['B12', 'B11', 'B8']},
        '12118a': {'label': 'PENETRACAO ATMOSFERICA - 12.11.8a', 'bands': ['B12', 'B11', 'B8A']},
        '8112': {'label': 'SAUDE DA VEGETACAO - 8.11.2', 'bands': ['B8', 'B11', 'B2']},
        '8a112': {'label': 'SAUDE DA VEGETACAO - 8a.11.2', 'bands': ['B8A', 'B11', 'B2']},
        '8114': {'label': 'SOLO/AGUA - 8.11.4', 'bands': ['B8', 'B11', 'B4']},
        '8a114': {'label': 'SOLO/AGUA - 8a.11.4', 'bands': ['B8A', 'B11', 'B4']},
        '1283': {'label': 'NATURAL COM REMOCAO ATMOSFERICA - 12.8.3', 'bands': ['B12', 'B8', 'B3']},
        '128a3': {'label': 'NATURAL COM REMOCAO ATMOSFERICA - 12.8a.3', 'bands': ['B12', 'B8A', 'B3']},
        '1284': {'label': 'INFRAVERMELHO ONDA CURTA - 12.8.4', 'bands': ['B12', 'B8', 'B4']},
        '128a4': {'label': 'INFRAVERMELHO ONDA CURTA - 12.8a.4', 'bands': ['B12', 'B8A', 'B4']},
        '1184': {'label': 'ANALISE DA VEGETACAO - 11.8.4', 'bands': ['B11', 'B8', 'B4']},
        '118a4': {'label': 'ANALISE DA VEGETACAO - 11.8a.4', 'bands': ['B11', 'B8A', 'B4']},
        '483': {'label': 'ANALISE DA VEGETACAO - 4.8.3', 'bands': ['B4', 'B8', 'B3']},
        'MB_10': {'label': 'MULTIBANDA - 10 BANDAS PRINCIPAIS (B2 a B12)', 'bands': ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12'], 'multiband': True},
        'MB_6': {'label': 'MULTIBANDA - 6 BANDAS VNIR/SWIR (B2, B3, B4, B8, B11, B12)', 'bands': ['B2', 'B3', 'B4', 'B8', 'B11', 'B12'], 'multiband': True},
        'MB_12': {'label': 'MULTIBANDA - 12 BANDAS COMPLETAS (B1 a B12)', 'bands': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12'], 'multiband': True},
        'NDVI': {'label': 'INDICE - NDVI (Vegetacao: B8-B4)', 'bands': ['B8', 'B4'], 'is_index': True},
        'NDWI': {'label': 'INDICE - NDWI (Agua: B3-B8)', 'bands': ['B3', 'B8'], 'is_index': True},
        'NDMI': {'label': 'INDICE - NDMI (Umidade: B8-B11)', 'bands': ['B8', 'B11'], 'is_index': True},
        'NBR':  {'label': 'INDICE - NBR (Queimadas: B8-B12)', 'bands': ['B8', 'B12'], 'is_index': True},
        'EVI':  {'label': 'INDICE - EVI (Vegetacao Realcada)', 'bands': ['B8', 'B4', 'B2'], 'is_index': True},
        'SAVI': {'label': 'INDICE - SAVI (Ajustado ao Solo)', 'bands': ['B8', 'B4'], 'is_index': True},
        'CUSTOM_MATH': {'label': 'INDICE - FORMULA PERSONALIZADA...', 'bands': [], 'is_index': True, 'is_custom': True}
    }
}
COMPOSITIONS['L4'] = COMPOSITIONS['L5']
COMPOSITIONS['L3'] = COMPOSITIONS['L1']
COMPOSITIONS['L2'] = COMPOSITIONS['L1']

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {'project': ''}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print("Erro salvando config:", e)

CREDENTIALS_PATH = os.path.expanduser('~/.config/earthengine/credentials')

def has_credentials():
    return os.path.exists(CREDENTIALS_PATH)

def init_gee(project=None):
    if not has_credentials():
        return False, "Nao autenticado no Google Earth Engine. Clique no botao 'Autenticar' para conectar sua conta Google."

    cfg = load_config()
    proj = project or cfg.get('project') or os.environ.get('EARTHENGINE_PROJECT') or None
    try:
        if proj:
            ee.Initialize(project=proj)
        else:
            ee.Initialize()
        return True, "Conectado ao Google Earth Engine! (Projeto: %s)" % (proj or "Padrao")
    except Exception as e:
        err_msg = str(e)
        if "API has not been used" in err_msg or "SERVICE_DISABLED" in err_msg:
            return False, "A API do Earth Engine nao esta habilitada no projeto '%s'. Habilite no Google Cloud Console ou informe outro ID de projeto." % (proj or "")
        return False, err_msg

def authenticate_gee(project=None):
    try:
        ee.Authenticate(auth_mode='localhost')
        if project:
            cfg = load_config()
            cfg['project'] = project
            save_config(cfg)
        return init_gee(project)
    except Exception as e:
        return False, str(e)

# Alias de compatibilidade
init_ee = init_gee

def apply_sensor_scaling(img, sensor):
    if sensor == 'S2':
        return img.divide(10000.0)
    elif sensor in ['L8', 'L7', 'L5', 'L4']:
        return img.multiply(0.0000275).add(-0.2)
    else:
        # MSS L1-3
        return img.divide(255.0)

INDEX_PALETTES = {
    'NDVI': {'min': -0.2, 'max': 0.85, 'palette': ['#0000ff', '#ffffff', '#e0f3f8', '#fee08b', '#d9ef8b', '#91cf60', '#1a9850', '#00441b']},
    'NDWI': {'min': -0.5, 'max': 0.5, 'palette': ['#8c510a', '#d8b365', '#f6e8c3', '#c7eae5', '#5ab4ac', '#01665e']},
    'NDMI': {'min': -0.5, 'max': 0.5, 'palette': ['#8c510a', '#d8b365', '#f6e8c3', '#c7eae5', '#5ab4ac', '#01665e']},
    'NBR':  {'min': -0.4, 'max': 0.8, 'palette': ['#000000', '#d73027', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b', '#a6d96a', '#1a9850']},
    'EVI':  {'min': -0.1, 'max': 0.8, 'palette': ['#0000ff', '#ffffff', '#fee08b', '#d9ef8b', '#91cf60', '#1a9850']},
    'SAVI': {'min': -0.1, 'max': 0.8, 'palette': ['#0000ff', '#ffffff', '#fee08b', '#d9ef8b', '#91cf60', '#1a9850']},
    'CUSTOM_MATH': {'min': -1.0, 'max': 1.0, 'palette': ['#0000ff', '#ffffff', '#ff0000']}
}

def compute_spectral_index(img, sensor, comp_code, custom_formula=None):
    """Calcula indice espectral ou formula customizada sobre a imagem (usando reflectancia normalizada)"""
    scaled = apply_sensor_scaling(img, sensor)

    # 1. Formula Matematica Customizada
    if comp_code == 'CUSTOM_MATH' or (custom_formula and ('(' in custom_formula or '+' in custom_formula or '-' in custom_formula or '/' in custom_formula or '*' in custom_formula)):
        formula = custom_formula or comp_code
        band_names = scaled.bandNames().getInfo()
        b_dict = {}
        for b in band_names:
            b_dict[b] = scaled.select(b)
            b_dict[b.lower()] = scaled.select(b)
            b_dict[b.upper()] = scaled.select(b)
        return scaled.expression(formula, b_dict).rename('CUSTOM_INDEX').toFloat()

    # Mapeamento padrao de bandas por sensor
    if sensor == 'S2':
        b_blue, b_green, b_red, b_nir, b_swir1, b_swir2 = 'B2', 'B3', 'B4', 'B8', 'B11', 'B12'
    elif sensor == 'L8':
        b_blue, b_green, b_red, b_nir, b_swir1, b_swir2 = 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'
    elif sensor in ['L7', 'L5', 'L4']:
        b_blue, b_green, b_red, b_nir, b_swir1, b_swir2 = 'SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'
    else:
        # L1-L3 MSS
        b_blue, b_green, b_red, b_nir, b_swir1, b_swir2 = 'B4', 'B4', 'B5', 'B7', 'B7', 'B7'

    if comp_code == 'NDVI':
        return scaled.normalizedDifference([b_nir, b_red]).rename('NDVI').toFloat()
    elif comp_code == 'NDWI':
        return scaled.normalizedDifference([b_green, b_nir]).rename('NDWI').toFloat()
    elif comp_code == 'NDMI':
        return scaled.normalizedDifference([b_nir, b_swir1]).rename('NDMI').toFloat()
    elif comp_code == 'NBR':
        return scaled.normalizedDifference([b_nir, b_swir2]).rename('NBR').toFloat()
    elif comp_code == 'EVI':
        return scaled.expression(
            '2.5 * ((NIR - RED) / (NIR + 6.0 * RED - 7.5 * BLUE + 1.0))',
            {'NIR': scaled.select(b_nir), 'RED': scaled.select(b_red), 'BLUE': scaled.select(b_blue)}
        ).rename('EVI').toFloat()
    elif comp_code == 'SAVI':
        return scaled.expression(
            '1.5 * ((NIR - RED) / (NIR + RED + 0.5))',
            {'NIR': scaled.select(b_nir), 'RED': scaled.select(b_red)}
        ).rename('SAVI').toFloat()

    return scaled.normalizedDifference([b_nir, b_red]).rename(comp_code).toFloat()

def get_visualization_image(img, sensor, composition_code):
    comp_map = COMPOSITIONS.get(sensor, COMPOSITIONS['L8'])
    comp_info = comp_map.get(composition_code, {})

    # Se for indice espectral, visualiza com a rampa de cores do indice
    if comp_info.get('is_index', False) or composition_code in INDEX_PALETTES:
        idx_img = compute_spectral_index(img, sensor, composition_code)
        pal_info = INDEX_PALETTES.get(composition_code, INDEX_PALETTES['NDVI'])
        return idx_img.visualize(min=pal_info['min'], max=pal_info['max'], palette=pal_info['palette'])

    if composition_code not in comp_map:
        first_code = list(comp_map.keys())[0]
        bands = comp_map[first_code]['bands']
    else:
        bands = comp_info['bands']

    # Se for multibanda, usa bandas padrao RGB para visualizacao da miniatura
    if len(bands) > 3:
        if sensor == 'S2':
            bands = ['B4', 'B3', 'B2']
        else:
            bands = ['SR_B4', 'SR_B3', 'SR_B2']

    scaled = apply_sensor_scaling(img, sensor)
    vis_params = {
        'bands': bands,
        'min': 0.0,
        'max': 0.7,
        'gamma': 1.2
    }
    return scaled.visualize(**vis_params)

def normalize_date(d_str):
    if not d_str:
        return ""
    d_str = str(d_str).strip()
    import re
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", d_str)
    if m:
        day, month, year = m.groups()
        return "%04d-%02d-%02d" % (int(year), int(month), int(day))
    m2 = re.match(r"^(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})$", d_str)
    if m2:
        year, month, day = m2.groups()
        return "%04d-%02d-%02d" % (int(year), int(month), int(day))
    return d_str

def parse_ee_geometry(geom_dict):
    """Converte com seguranca qualquer formato GeoJSON (Polygon, MultiPolygon, Feature, FeatureCollection) para ee.Geometry"""
    if not geom_dict:
        return None
    gtype = geom_dict.get('type')
    if gtype == 'FeatureCollection':
        return ee.FeatureCollection(geom_dict).geometry()
    elif gtype == 'Feature':
        return ee.Feature(geom_dict).geometry()
    elif gtype in ['Polygon', 'MultiPolygon', 'Point', 'MultiPoint', 'LineString', 'MultiLineString', 'GeometryCollection']:
        return ee.Geometry(geom_dict)
    elif 'coordinates' in geom_dict:
        return ee.Geometry(geom_dict)
    elif 'features' in geom_dict:
        return ee.FeatureCollection(geom_dict).geometry()
    return ee.Geometry(geom_dict)

def search_collection(sensor, start_date, end_date, bbox=None, geometry=None, path=None, row=None, mgrs=None, max_images=150):
    coll = get_image_collection(sensor)

    # Filtro temporal inclusivo com normalizacao de formato (suporta DD/MM/AAAA e AAAA-MM-DD)
    s_date = normalize_date(start_date)
    e_date = normalize_date(end_date)
    if s_date and e_date:
        end_dt_str = e_date
        if len(end_dt_str) == 10:
            import datetime
            try:
                d = datetime.datetime.strptime(end_dt_str, "%Y-%m-%d").date() + datetime.timedelta(days=1)
                end_dt_str = d.strftime("%Y-%m-%d")
            except Exception:
                pass
        coll = coll.filterDate(s_date, end_dt_str)

    # Filtro espacial estrito: Extensao da tela (bbox) ou Camada Vetorial (geometry)
    aoi = None
    if geometry:
        aoi = parse_ee_geometry(geometry)
    elif bbox:
        # [minx, miny, maxx, maxy]
        aoi = ee.Geometry.BBox(bbox[0], bbox[1], bbox[2], bbox[3])
    else:
        raise ValueError(u"Filtro espacial obrigatório: defina a extensão da tela do ArcMap ou selecione uma camada vetorial (AOI).")

    coll = coll.filterBounds(aoi)

    # Ordenar por data (mais recentes primeiro) e limitar
    coll = coll.sort('system:time_start', False).limit(max_images)

    # Obter lista de imagens de forma direta e rapida
    data = coll.getInfo()
    features = data.get('features', [])

    results = []
    import datetime
    for f in features:
        full_id = f.get('id', '')
        short_name = full_id.split('/')[-1]
        p = f.get('properties', {})

        t_ms = p.get('system:time_start', 0)
        dt_str = datetime.datetime.utcfromtimestamp(t_ms / 1000.0).strftime('%Y-%m-%d %H:%M') if t_ms else 'N/A'

        # Nuvem
        cloud_val = p.get('CLOUDY_PIXEL_PERCENTAGE')
        if cloud_val is None:
            cloud_val = p.get('CLOUD_COVER', 0.0)
        try:
            cloud = round(float(cloud_val), 1)
        except Exception:
            cloud = 0.0

        tile_val = p.get('MGRS_TILE') or ''
        path_val = p.get('WRS_PATH') or ''
        row_val = p.get('WRS_ROW') or ''

        results.append({
            'id': full_id,
            'name': short_name,
            'date': dt_str,
            'cloud_pct': cloud,
            'mgrs': tile_val,
            'path': path_val,
            'row': row_val
        })

    return results

def get_thumbnail_url(image_id, sensor, composition_code, dimensions=350, bbox=None):
    coll_id = COLLECTIONS.get(sensor, '')
    if coll_id and '/' not in image_id:
        image_id = coll_id + '/' + image_id

    img = ee.Image(image_id)
    vis_img = get_visualization_image(img, sensor, composition_code)
    
    thumb_params = {
        'dimensions': dimensions,
        'format': 'png',
        'crs': 'EPSG:3857'
    }
    if bbox:
        thumb_params['region'] = ee.Geometry.BBox(bbox[0], bbox[1], bbox[2], bbox[3])
    
    return vis_img.getThumbURL(thumb_params)

def compute_safe_scale(region_bbox, num_bands, is_multiband, requested_scale=None, sensor=None):
    """
    Verifica se a resolucao nativa solicitada cabe no limite de 48 MB do GEE.
    REGRA RIGOROSA: NUNCA diminuir qualidade/reamostrar silenciosamente!
    Se a resolucao nativa estourar o limite de 48 MB, lanca ValueError para impedir o download com perda de qualidade.
    """
    import math
    req = None
    if requested_scale is not None:
        try:
            req = float(requested_scale)
        except Exception:
            req = None

    if req is None or req <= 0:
        if sensor == 'S2':
            req = 10.0
        elif sensor in ['L8', 'L7', 'L5', 'L4']:
            req = 30.0
        elif sensor in ['L1', 'L2', 'L3']:
            req = 60.0
        else:
            req = 20.0 if num_bands > 3 else 30.0

    if not region_bbox:
        return req

    minx, miny, maxx, maxy = region_bbox
    lat_center = (miny + maxy) / 2.0
    lat_rad = math.radians(lat_center)

    width_m = abs(maxx - minx) * 111320.0 * math.cos(lat_rad)
    height_m = abs(maxy - miny) * 110540.0
    area_m2 = max(width_m * height_m, 1000.0)

    bytes_per_pixel = 4 if (num_bands == 1 and not is_multiband) else ((2 * num_bands) if is_multiband else 3)
    target_max_bytes = 48 * 1024 * 1024  # 48 MB limite maximo do GEE
    max_pixels = float(target_max_bytes) / float(bytes_per_pixel)

    min_safe_scale = math.sqrt(area_m2 / max_pixels)

    if min_safe_scale > req * 1.05:  # Tolerancia de 5%
        area_km2 = area_m2 / 1000000.0
        est_mb = round((area_m2 / (req * req) * bytes_per_pixel) / (1024.0 * 1024.0), 1)
        raise ValueError(
            u"A área selecionada (%.0f km²) excede o limite do Google Earth Engine para a resolução nativa de %.1fm com %d bandas (tamanho estimado: %.1f MB, limite: 48 MB).\n\n"
            u"Para garantir 100%% da qualidade da imagem sem qualquer perda por reamostragem, o download foi cancelado.\n\n"
            u"Solução: Aproxime o zoom no ArcMap (escala <= 1:250.000) ou utilize uma camada vetorial (AOI) menor." % (
                area_km2, req, num_bands, est_mb
            )
        )

    return req

def download_geotiff(image_ids, sensor, composition_code, custom_bands=None, load_mode='multiband', aoi_geometry=None, bbox=None, out_tif_path=None, scale=None, crs='EPSG:4674'):
    import math
    import re

    if not image_ids:
        raise ValueError("Nenhum ID de imagem fornecido.")

    cleaned_ids = []
    for img_id in image_ids:
        if '/' not in img_id:
            coll_id = COLLECTIONS.get(sensor, '')
            if coll_id:
                cleaned_ids.append(coll_id + '/' + img_id)
            else:
                cleaned_ids.append(img_id)
        else:
            cleaned_ids.append(img_id)

    if len(cleaned_ids) == 1:
        img = ee.Image(cleaned_ids[0])
    else:
        coll = ee.ImageCollection(cleaned_ids)
        img = coll.median()

    comp_map = COMPOSITIONS.get(sensor, COMPOSITIONS['L8'])
    comp_info = comp_map.get(composition_code, {})

    is_index = comp_info.get('is_index', False) or composition_code in ['NDVI', 'NDWI', 'NDMI', 'NBR', 'EVI', 'SAVI', 'CUSTOM_MATH']

    if is_index:
        is_multi = False
        bands = [composition_code]
        formula = custom_bands if composition_code == 'CUSTOM_MATH' else None
        export_img = compute_spectral_index(img, sensor, composition_code, custom_formula=formula)
    elif (load_mode == 'multiband') or comp_info.get('multiband', False) or (custom_bands and len(custom_bands.split(',')) > 3):
        is_multi = True
        if custom_bands:
            bands = [b.strip() for b in custom_bands.split(',') if b.strip()]
        elif comp_info.get('bands'):
            bands = comp_info['bands']
        else:
            bands = MULTIBAND_DEFAULT_BANDS.get(sensor, ['B4', 'B3', 'B2'])
        export_img = img.select(bands)
    else:
        if custom_bands:
            bands = [b.strip() for b in custom_bands.split(',') if b.strip()][:3]
        else:
            bands = comp_info.get('bands', ['B4', 'B3', 'B2'])[:3]

        scaled = apply_sensor_scaling(img, sensor)
        vis_params = {
            'bands': bands,
            'min': 0.0,
            'max': 0.7,
            'gamma': 1.2
        }
        export_img = scaled.visualize(**vis_params)

    region = None
    calc_bbox = None
    if aoi_geometry:
        region = parse_ee_geometry(aoi_geometry)
        try:
            all_pts = []
            def extract_pts(c):
                if isinstance(c, (list, tuple)):
                    if len(c) >= 2 and isinstance(c[0], (int, float)):
                        all_pts.append(c)
                    else:
                        for sub in c:
                            extract_pts(sub)
            coords = aoi_geometry.get('coordinates', [])
            extract_pts(coords)
            if not all_pts and 'features' in aoi_geometry:
                for ft in aoi_geometry.get('features', []):
                    extract_pts(ft.get('geometry', {}).get('coordinates', []))
            if all_pts:
                xs = [p[0] for p in all_pts]
                ys = [p[1] for p in all_pts]
                calc_bbox = [min(xs), min(ys), max(xs), max(ys)]
        except Exception:
            pass
    elif bbox:
        region = ee.Geometry.BBox(bbox[0], bbox[1], bbox[2], bbox[3])
        calc_bbox = bbox
    else:
        raise ValueError(u"Filtro espacial obrigatório: defina a extensão da tela do mapa ou selecione uma camada vetorial (AOI).")

    safe_scale = compute_safe_scale(calc_bbox, len(bands), is_multi, requested_scale=scale, sensor=sensor)

    download_params = {
        'scale': safe_scale,
        'crs': crs,
        'region': region,
        'format': 'GEO_TIFF'
    }

    url = None
    try:
        url = export_img.getDownloadURL(download_params)
    except Exception as e:
        err_str = str(e)
        m = re.search(r'Total request size \((\d+) bytes\) must be less than or equal to (\d+) bytes', err_str)
        if m:
            req_mb = round(float(m.group(1)) / (1024.0 * 1024.0), 1)
            limit_mb = round(float(m.group(2)) / (1024.0 * 1024.0), 1)
            raise ValueError(
                u"O volume da área solicitada (%.1f MB) excede o limite de transferência do Google Earth Engine (%.1f MB) na resolução nativa de %.1fm com %d bandas.\n\n"
                u"Para garantir 100%% da nitidez e qualidade original sem qualquer perda, o download não foi realizado.\n\n"
                u"Por favor, aumente o zoom no ArcMap (escala <= 1:250.000) ou utilize uma camada vetorial (AOI) menor." % (
                    req_mb, limit_mb, safe_scale, len(bands)
                )
            )
        else:
            raise e

    if not url:
        raise RuntimeError("Falha ao obter URL de download do GEE.")

    if not out_tif_path:
        first_name = cleaned_ids[0].split('/')[-1]
        out_tif_path = os.path.join(tempfile.gettempdir(), "%s_%s.tif" % (first_name, composition_code))

    os.makedirs(os.path.dirname(os.path.abspath(out_tif_path)), exist_ok=True)
    urllib.request.urlretrieve(url, out_tif_path)
    return out_tif_path
