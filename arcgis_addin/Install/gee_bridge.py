# -*- coding: utf-8 -*-
"""
Ponte de Comunicacao entre ArcMap 10.8 (Python 2.7) e Backend GEE (Python 3)
"""

import os
import sys
import json
import time
import tempfile
import subprocess

try:
    import arcpy
except ImportError:
    arcpy = None

def find_python3():
    # 1. Variavel de ambiente explicita
    env_py = os.environ.get('GEE_PYTHON3')
    if env_py and os.path.exists(env_py):
        return env_py

    # 2. Configuracao salva do plugin
    try:
        settings = load_plugin_settings()
        custom_py3 = settings.get('python3_path')
        if custom_py3 and os.path.exists(custom_py3):
            return custom_py3
    except Exception:
        pass

    # 3. Lista de caminhos comuns no Windows
    candidates = [
        r"C:\CGMA_GEE_PLUGIN\venv\Scripts\python.exe",
        r"C:\PRODUTIVIDADE_SIMCAR_DIGITAL\venv_p3\Scripts\python.exe",
        r"C:\Program Files\QGIS 3.44.10\apps\Python312\python.exe",
        r"C:\Program Files\QGIS 3.34.10\apps\Python312\python.exe",
        r"C:\Program Files\QGIS 3.28\apps\Python39\python.exe",
        r"C:\Python312\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Python310\python.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\python.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311\python.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python310\python.exe"),
        r"python.exe"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "python.exe"

def get_backend_script():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 1. Subpasta backend dentro de Install (Add-In autocontido no AssemblyCache)
    p0 = os.path.join(current_dir, "backend", "run_gee.py")
    if os.path.exists(p0):
        return os.path.abspath(p0)

    # 2. Na raiz do repositorio (backend/run_gee.py)
    p1 = os.path.join(current_dir, "..", "..", "backend", "run_gee.py")
    if os.path.exists(p1):
        return os.path.abspath(p1)

    p1_alt = os.path.join(current_dir, "..", "backend", "run_gee.py")
    if os.path.exists(p1_alt):
        return os.path.abspath(p1_alt)

    # 3. Na mesma pasta
    p2 = os.path.join(current_dir, "run_gee.py")
    if os.path.exists(p2):
        return os.path.abspath(p2)

    return os.path.abspath(p0)

# Definicoes locais de composicoes de bandas para resposta instantanea (zero subprocessos ao abrir janela)
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

def run_backend_cmd(subcmd, args_dict):
    py3 = find_python3()
    script = get_backend_script()
    if not os.path.exists(script):
        return {'success': False, 'message': u"Script backend nao encontrado: " + unicode(script)}

    cmd = [py3, script, subcmd]
    for k, v in args_dict.items():
        if v is not None and unicode(v).strip() != u"":
            flag = "--" + k.replace("_", "-")
            cmd.append("%s=%s" % (flag, unicode(v)))

    try:
        # Sanitizar variaveis de ambiente para isolar Python 3 do ambiente Python 2 do ArcMap
        clean_env = dict(os.environ)
        clean_env.pop('PYTHONPATH', None)
        clean_env.pop('PYTHONHOME', None)

        # Configurar para nao abrir janela preta do cmd
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            env=clean_env
        )
        out, err = proc.communicate()

        if proc.returncode != 0 and not out:
            return {'success': False, 'message': u"Erro executando backend (codigo %d): %s" % (proc.returncode, unicode(err, errors='ignore'))}

        # Filtrar saida para encontrar a linha JSON
        lines = out.strip().splitlines()
        json_line = lines[-1] if lines else "{}"
        data = json.loads(json_line)
        return data
    except Exception as e:
        return {'success': False, 'message': u"Excecao na execucao do backend: " + unicode(e)}

def check_gee(project=None):
    return run_backend_cmd("check", {"project": project})

def authenticate_gee(project=None):
    return run_backend_cmd("auth", {"project": project})

def launch_auth_console(project=None):
    """Abre uma janela de console interativa com earthengine authenticate para o usuario logar no navegador"""
    py3 = find_python3()
    py_dir = os.path.dirname(py3)
    ee_exe = os.path.join(py_dir, "earthengine.exe")
    if not os.path.exists(ee_exe):
        ee_exe = "earthengine"

    # Salvar projeto na config se fornecido
    if project:
        script = get_backend_script()
        cfg_file = os.path.join(os.path.dirname(script), "gee_config.json")
        try:
            with open(cfg_file, 'w') as f:
                json.dump({"project": project}, f, indent=2)
        except Exception:
            pass

    cmd = 'start "Google Earth Engine - Autenticacao" cmd /k ""%s" authenticate --auth_mode=localhost && echo. && echo ======================================================== && echo [SUCESSO] Autenticacao salva! && echo Voce ja pode fechar esta janela e voltar ao ArcMap. && echo ======================================================== && pause"' % ee_exe
    try:
        subprocess.Popen(cmd, shell=True)
        return True, "Janela de autenticacao aberta. Siga as instrucoes no navegador."
    except Exception as e:
        return False, str(e)

def get_compositions(sensor):
    comps = COMPOSITIONS.get(sensor, {})
    return {'success': True, 'compositions': comps}

def search_images(sensor, start_date, end_date, bbox=None, geojson_file=None, path=None, row=None, mgrs=None, max_images=100, project=None):
    bbox_str = ",".join(str(x) for x in bbox) if bbox else None
    return run_backend_cmd("search", {
        "sensor": sensor,
        "start_date": start_date,
        "end_date": end_date,
        "bbox": bbox_str,
        "geojson_file": geojson_file,
        "path": path,
        "row": row,
        "mgrs": mgrs,
        "max_images": max_images,
        "project": project
    })

def get_thumbnail(image_id, sensor, comp_code, out_png, bbox=None, project=None):
    bbox_str = ",".join(str(x) for x in bbox) if bbox else None
    return run_backend_cmd("thumb", {
        "image_id": image_id,
        "sensor": sensor,
        "comp": comp_code,
        "out": out_png,
        "bbox": bbox_str,
        "project": project
    })

def download_image(image_ids, sensor, comp_code, out_tif, custom_bands=None, load_mode="multiband", bbox=None, geojson_file=None, scale=None, crs="EPSG:4674", project=None):
    ids_str = ",".join(image_ids) if isinstance(image_ids, (list, tuple)) else str(image_ids)
    bbox_str = ",".join(str(x) for x in bbox) if bbox else None
    return run_backend_cmd("download", {
        "ids": ids_str,
        "sensor": sensor,
        "comp": comp_code,
        "custom_bands": custom_bands,
        "load_mode": load_mode,
        "out": out_tif,
        "bbox": bbox_str,
        "geojson_file": geojson_file,
        "scale": scale,
        "crs": crs,
        "project": project
    })

def get_arcmap_scale():
    """Retorna o denominador da escala do mapa atual do ArcMap (ex: 250000 para 1:250.000)"""
    if not arcpy:
        return None
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        return df.scale
    except Exception:
        return None

def set_arcmap_scale(new_scale):
    """Ajusta a escala do mapa no ArcMap para um valor especifico (ex: 500000 para 1:500.000)"""
    if not arcpy:
        return False
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        df.scale = float(new_scale)
        arcpy.RefreshActiveView()
        return True
    except Exception:
        return False

def get_arcmap_extent_wgs84():
    """Retorna [minx, miny, maxx, maxy] da tela ativa do ArcMap em WGS84"""
    if not arcpy:
        return None
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        ext = df.extent
        sr_wgs84 = arcpy.SpatialReference(4326)
        ext_wgs = ext.projectAs(sr_wgs84)
        return [ext_wgs.XMin, ext_wgs.YMin, ext_wgs.XMax, ext_wgs.YMax]
    except Exception as e:
        print("Erro obtendo extensao ArcMap:", e)
        return None

def get_arcmap_layers():
    """Lista camadas vetoriais disponiveis no TOC do ArcMap"""
    if not arcpy:
        return []
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        layers = arcpy.mapping.ListLayers(mxd)
        return [lyr.name for lyr in layers if lyr.isFeatureLayer]
    except Exception:
        return []

def get_arcmap_raster_layers():
    """Lista todas as camadas raster presentes no TOC do ArcMap para mapeamento e substituicao"""
    if not arcpy:
        return []
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        layers = arcpy.mapping.ListLayers(mxd)
        rasters = []
        for lyr in layers:
            if not lyr.isGroupLayer and lyr.isRasterLayer:
                rasters.append(lyr.longName)
        return rasters
    except Exception as e:
        print("Erro listando camadas raster:", e)
        return []

def export_layer_to_geojson(layer_name, out_geojson, buffer_meters=None):
    """Exporta o retangulo envolvente (envelope) da camada ativa para GeoJSON em WGS84 com buffer opcional em metros"""
    if not arcpy:
        return None
    try:
        import math
        mxd = arcpy.mapping.MapDocument("CURRENT")
        layers = arcpy.mapping.ListLayers(mxd, layer_name)
        if not layers:
            return None
        lyr = layers[0]
        sr_wgs84 = arcpy.SpatialReference(4326)

        if buffer_meters is None:
            settings = load_plugin_settings()
            buffer_meters = float(settings.get('aoi_buffer_meters', 1000.0))
        else:
            buffer_meters = float(buffer_meters)

        ext = lyr.getExtent()
        if not ext:
            return None

        # Verificar se o sistema da camada e projetado (unidade linear metros)
        sr = ext.spatialReference
        if sr and sr.type == 'Projected' and buffer_meters > 0:
            minx = ext.XMin - buffer_meters
            miny = ext.YMin - buffer_meters
            maxx = ext.XMax + buffer_meters
            maxy = ext.YMax + buffer_meters
            ext_buffered = arcpy.Extent(minx, miny, maxx, maxy, sr)
            ext_wgs = ext_buffered.projectAs(sr_wgs84)
            minx_wgs, miny_wgs, maxx_wgs, maxy_wgs = ext_wgs.XMin, ext_wgs.YMin, ext_wgs.XMax, ext_wgs.YMax
        else:
            ext_wgs = ext.projectAs(sr_wgs84)
            minx_wgs, miny_wgs, maxx_wgs, maxy_wgs = ext_wgs.XMin, ext_wgs.YMin, ext_wgs.XMax, ext_wgs.YMax
            if buffer_meters > 0:
                lat_c = (miny_wgs + maxy_wgs) / 2.0
                d_lat = buffer_meters / 110574.0
                cos_lat = max(0.01, math.cos(math.radians(lat_c)))
                d_lon = buffer_meters / (111320.0 * cos_lat)
                minx_wgs -= d_lon
                miny_wgs -= d_lat
                maxx_wgs += d_lon
                maxy_wgs += d_lat

        # Retangulo envolvente em GeoJSON Polygon estrito (padrao RFC 7946)
        bbox_poly = [
            [minx_wgs, miny_wgs],
            [maxx_wgs, miny_wgs],
            [maxx_wgs, maxy_wgs],
            [minx_wgs, maxy_wgs],
            [minx_wgs, miny_wgs]
        ]
        geojson_data = {
            "type": "Polygon",
            "coordinates": [bbox_poly]
        }

        with open(out_geojson, "w") as f:
            json.dump(geojson_data, f, indent=2)
        return out_geojson
    except Exception as e:
        print("Erro exportando camada para GeoJSON:", e)
        return None

def get_empty_group_lyr_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "empty_group_template.lyr"),
        os.path.join(current_dir, "Install", "empty_group_template.lyr"),
        r"C:\Users\joberthgambati\.gemini\antigravity\scratch\gee_arcgis_plugin\arcgis_addin\Install\empty_group_template.lyr"
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None

def ensure_pure_group_template():
    """Garante que empty_group_template.lyr seja um GroupLayer comum (e NUNCA um BasemapLayer)"""
    tmpl_path = get_empty_group_lyr_path()
    need_create = True
    if tmpl_path and os.path.exists(tmpl_path):
        try:
            l = arcpy.mapping.Layer(tmpl_path)
            if l.isGroupLayer and not l.isBasemapLayer:
                need_create = False
        except Exception:
            pass

    if need_create:
        try:
            import comtypes.client
            esriCarto = comtypes.client.GetModule(r'C:\Program Files (x86)\ArcGIS\Desktop10.8\com\esriCarto.olb')
            gl = comtypes.client.CreateObject(esriCarto.GroupLayer, interface=esriCarto.IGroupLayer)
            out_p = tmpl_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "empty_group_template.lyr")
            lf = comtypes.client.CreateObject(esriCarto.LayerFile, interface=esriCarto.ILayerFile)
            if os.path.exists(out_p):
                try: os.remove(out_p)
                except Exception: pass
            lf.New(out_p)
            lf.ReplaceContents(gl)
            lf.Save()
            lf.Close()
            return out_p
        except Exception as ex:
            print("Erro gerando template de grupo:", ex)
    return tmpl_path

def get_or_create_group_layer(group_name):
    """Localiza ou cria um Grupo de Camadas Comum (Group Layer normal, NUNCA Basemap Layer) no ArcMap"""
    if not arcpy or not group_name or not unicode(group_name).strip():
        return None
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        gname = unicode(group_name).strip()

        # 1. Procurar se ja existe um grupo com este nome
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            if lyr.isGroupLayer and lyr.name.strip().lower() == gname.lower():
                if lyr.isBasemapLayer:
                    # Se for basemap layer (erro da versao anterior), remover do TOC para substituir por grupo comum
                    try:
                        arcpy.mapping.RemoveLayer(df, lyr)
                    except Exception:
                        pass
                    break
                else:
                    return lyr

        # 2. Criar a partir do template de grupo comum (garantido isBasemapLayer == False)
        tmpl_path = ensure_pure_group_template()
        if tmpl_path and os.path.exists(tmpl_path):
            grp_tmpl = arcpy.mapping.Layer(tmpl_path)
            grp_tmpl.name = gname
            grp_tmpl.visible = True
            arcpy.mapping.AddLayer(df, grp_tmpl, "TOP")

            for lyr in arcpy.mapping.ListLayers(mxd, "", df):
                if lyr.isGroupLayer and not lyr.isBasemapLayer and lyr.name.strip().lower() == gname.lower():
                    return lyr
        return None
    except Exception as e:
        print("Erro ao criar/obter grupo comum:", e)
        return None

BAND_NAME_TO_INDEX = {
    'S2': {
        'B2': 1, 'B3': 2, 'B4': 3, 'B5': 4, 'B6': 5, 'B7': 6, 'B8': 7, 'B8A': 8, 'B11': 9, 'B12': 10
    },
    'L8': {
        'SR_B1': 1, 'SR_B2': 2, 'SR_B3': 3, 'SR_B4': 4, 'SR_B5': 5, 'SR_B6': 6, 'SR_B7': 7
    },
    'L7': {
        'SR_B1': 1, 'SR_B2': 2, 'SR_B3': 3, 'SR_B4': 4, 'SR_B5': 5, 'SR_B7': 6
    },
    'L5': {
        'SR_B1': 1, 'SR_B2': 2, 'SR_B3': 3, 'SR_B4': 4, 'SR_B5': 5, 'SR_B7': 6
    },
    'L4': {
        'SR_B1': 1, 'SR_B2': 2, 'SR_B3': 3, 'SR_B4': 4, 'SR_B5': 5, 'SR_B7': 6
    },
    'L3': {
        'B4': 1, 'B5': 2, 'B6': 3, 'B7': 4
    },
    'L2': {
        'B4': 1, 'B5': 2, 'B6': 3, 'B7': 4
    },
    'L1': {
        'B4': 1, 'B5': 2, 'B6': 3, 'B7': 4
    }
}

def get_band_indices_for_composition(sensor, comp_code):
    """Retorna os indices [R, G, B] (1-based) para a composicao do sensor"""
    comps = COMPOSITIONS.get(sensor, {})
    comp_info = comps.get(comp_code, {})
    bands = comp_info.get('bands')
    if not bands or len(bands) < 3:
        return None
    name_map = BAND_NAME_TO_INDEX.get(sensor, {})
    indices = []
    for b in bands[:3]:
        idx = name_map.get(b)
        if idx:
            indices.append(idx)
    if len(indices) == 3:
        return indices
    return None

SETTINGS_FILE = os.path.expanduser("~/.gee_plugin_settings.json")

def load_plugin_settings():
    """Carrega as configuracoes persistentes do plugin ou retorna os padroes"""
    defaults = {
        'stretch_type': 'Standard Deviations',
        'stretch_std_param': 2.0,
        'statistics_type': 'From Current Display Extent',
        'multicore_enabled': True,
        'multicore_cores': 4,
        'aoi_buffer_meters': 1000.0
    }
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                defaults.update(data)
    except Exception:
        pass
    return defaults

def save_plugin_settings(settings):
    """Salva as configuracoes do plugin no arquivo persistente"""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print("Erro salvando configuracoes:", e)
        return False

def resolve_rgb_band_indices(sensor, comp_code, custom_bands=None, band_count=None):
    """Retorna os indices 0-based [R, G, B] para a simbologia do raster baixado,
    preservando todas as bandas no raster e direcionando as cores iniciais."""
    raster_bands = []
    if custom_bands:
        if isinstance(custom_bands, (list, tuple)):
            raster_bands = [str(b).strip() for b in custom_bands if str(b).strip()]
        elif isinstance(custom_bands, basestring):
            raster_bands = [b.strip() for b in custom_bands.split(',') if b.strip()]
    
    if not raster_bands:
        comp_info = COMPOSITIONS.get(sensor, {}).get(comp_code, {})
        if comp_info.get('bands'):
            raster_bands = comp_info['bands']

    target_comp_bands = COMPOSITIONS.get(sensor, {}).get(comp_code, {}).get('bands', [])
    if len(target_comp_bands) < 3:
        target_comp_bands = ['B4', 'B3', 'B2'] if sensor == 'S2' else ['SR_B4', 'SR_B3', 'SR_B2']

    if raster_bands and len(raster_bands) >= 3:
        if len(raster_bands) == 3 and not custom_bands:
            return (0, 1, 2)
        
        indices = []
        for tb in target_comp_bands[:3]:
            if tb in raster_bands:
                indices.append(raster_bands.index(tb))
            else:
                matched = False
                for r_idx, rb in enumerate(raster_bands):
                    if rb.replace("SR_", "") == tb.replace("SR_", ""):
                        indices.append(r_idx)
                        matched = True
                        break
                if not matched:
                    indices.append(None)
        
        used = [x for x in indices if x is not None]
        avail = [i for i in range(len(raster_bands)) if i not in used]
        final_indices = []
        for x in indices:
            if x is not None:
                final_indices.append(x)
            elif avail:
                final_indices.append(avail.pop(0))
            else:
                final_indices.append(0)
        return (final_indices[0], final_indices[1], final_indices[2])
    
    bc = band_count or 3
    return (0, 1 if bc > 1 else 0, 2 if bc > 2 else 0)

def apply_stretch_and_stats(lyr_file_path, settings=None, rgb_bands=None):
    """Aplica configuracoes de Stretch (Standard Deviations, Percent Clip, etc) 
    e Statistics (AreaOfView / Display Extent) ao arquivo de camada .lyr via ArcObjects."""
    if not settings:
        settings = load_plugin_settings()
    try:
        import comtypes.client
        esriCarto = comtypes.client.GetModule(r'C:\Program Files (x86)\ArcGIS\Desktop10.8\com\esriCarto.olb')
        lf = comtypes.client.CreateObject(esriCarto.LayerFile, interface=esriCarto.ILayerFile)
        lf.Open(lyr_file_path)
        layer = lf.Layer
        raster_layer = layer.QueryInterface(esriCarto.IRasterLayer)
        renderer = raster_layer.Renderer

        # Se rgb_bands fornecido e renderer for RGB, configurar indices das bandas (0-based)
        if rgb_bands and len(rgb_bands) >= 3:
            try:
                rgb_rend = renderer.QueryInterface(esriCarto.IRasterRGBRenderer)
                rgb_rend.RedBandIndex = int(rgb_bands[0])
                rgb_rend.GreenBandIndex = int(rgb_bands[1])
                rgb_rend.BlueBandIndex = int(rgb_bands[2])
            except Exception as e_rgb:
                pass

        # 1. Configurar Stretch Type
        st_map = {
            'Standard Deviations': esriCarto.esriRasterStretch_StandardDeviations,
            'Standard Deviation': esriCarto.esriRasterStretch_StandardDeviations,
            'Percent Clip': esriCarto.esriRasterStretch_PercentMinimumMaximum,
            'Minimum-Maximum': esriCarto.esriRasterStretch_MinimumMaximum,
            'Histogram Equalize': esriCarto.esriRasterStretch_HistogramEqualize,
            'None': esriCarto.esriRasterStretch_NONE,
            'Esri': esriCarto.esriRasterStretch_ESRI,
            'Sigmoid': esriCarto.esriRasterStretch_Sigmoid
        }
        st_choice = settings.get('stretch_type', 'Standard Deviations')
        st_val = st_map.get(st_choice, esriCarto.esriRasterStretch_StandardDeviations)

        try:
            stretch = renderer.QueryInterface(esriCarto.IRasterStretch)
            stretch.StretchType = st_val
            if st_val == esriCarto.esriRasterStretch_StandardDeviations:
                std_param = float(settings.get('stretch_std_param', 2.0))
                stretch.StandardDeviationsParam = std_param
        except Exception as e:
            print("Erro aplicando StretchType:", e)

        # 2. Configurar Statistics Type (AreaOfView = From Current Display Extent)
        stats_map = {
            'From Current Display Extent': esriCarto.esriRasterStretchStats_AreaOfView,
            'From Each Raster Dataset': esriCarto.esriRasterStretchStats_Dataset,
            'From Custom Settings': esriCarto.esriRasterStretchStats_GlobalStats
        }
        stats_choice = settings.get('statistics_type', 'From Current Display Extent')
        stats_val = stats_map.get(stats_choice, esriCarto.esriRasterStretchStats_AreaOfView)

        try:
            stretch2 = renderer.QueryInterface(esriCarto.IRasterStretch2)
            stretch2.StretchStatsType = stats_val
        except Exception as e:
            print("Erro aplicando StretchStatsType:", e)

        raster_layer.Renderer = renderer
        lf.Save()
        lf.Close()
        return True
    except Exception as ex:
        print("Erro em apply_stretch_and_stats:", ex)
        return False

def load_into_toc(tif_path, layer_name=None, group_name=None, zoom=False, comp_code=None, sensor=None, custom_bands=None):
    """Adiciona o arquivo GeoTIFF baixado diretamente no TOC do ArcMap sem duplicar,
    configurando a simbologia RGB com as bandas corretas e preservando todas as bandas (4 ou mais)."""
    if not arcpy:
        return False, "ArcPy nao disponivel."

    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]

        if not layer_name:
            layer_name = os.path.splitext(os.path.basename(tif_path))[0]

        tif_basename_ext   = os.path.basename(tif_path)
        tif_basename_noext = os.path.splitext(tif_basename_ext)[0]
        suspect_names = {tif_basename_ext, tif_basename_noext, layer_name}

        # Carregar configuracoes do plugin (Stretch, Statistics, Multicore)
        settings = load_plugin_settings()
        cores = settings.get('multicore_cores', 4) if settings.get('multicore_enabled', True) else 1

        # Ativar Multicore no ArcPy para geoprocessamento paralelo (CalculateStatistics, BuildPyramids)
        prev_parallel = getattr(arcpy.env, 'parallelProcessingFactor', None)
        try:
            arcpy.env.parallelProcessingFactor = str(cores)
        except Exception:
            pass

        # CRITICO: Desativar addOutputsToMap para que nenhuma ferramenta de geoprocessamento
        # (CalculateStatistics, BuildPyramids, MakeRasterLayer) auto-adicione camadas a raiz do TOC
        prev_add_outputs = arcpy.env.addOutputsToMap
        arcpy.env.addOutputsToMap = False
        try:
            # 1. Estatisticas de todas as bandas e piramides (executadas em multicore)
            try:
                arcpy.CalculateStatistics_management(tif_path, 1, 1, "", "OVERWRITE")
            except Exception:
                pass
            try:
                arcpy.BuildPyramids_management(tif_path)
            except Exception:
                pass

            # 2. Verificar numero de bandas
            desc = arcpy.Describe(tif_path)
            band_count = getattr(desc, 'bandCount', 1)

            # 3. Criar camada com simbologia RGB ou Stretched e aplicar Stretch/DRA padrao
            temp_lyr_name = "gee_tmp_" + str(abs(hash(tif_path)))[:6]
            arcpy.MakeRasterLayer_management(tif_path, temp_lyr_name)
            tmp_lyr_file = os.path.join(tempfile.gettempdir(), temp_lyr_name + ".lyr")
            try:
                if os.path.exists(tmp_lyr_file):
                    os.remove(tmp_lyr_file)
            except Exception:
                pass
            arcpy.SaveToLayerFile_management(temp_lyr_name, tmp_lyr_file)
            if band_count >= 3:
                rgb_indices = resolve_rgb_band_indices(sensor, comp_code, custom_bands, band_count)
                apply_stretch_and_stats(tmp_lyr_file, settings, rgb_bands=rgb_indices)
            else:
                apply_stretch_and_stats(tmp_lyr_file, settings, rgb_bands=None)
            layer_obj = arcpy.mapping.Layer(tmp_lyr_file)

            layer_obj.name = layer_name
            layer_obj.visible = True

            # 4. Obter ou criar grupo alvo se solicitado (sempre GroupLayer comum, nunca Basemap)
            target_grp = None
            if group_name and unicode(group_name).strip():
                target_grp = get_or_create_group_layer(group_name)

            # 5. Inserir camada: dentro do grupo (AddLayerToGroup) ou na raiz (AddLayer)
            if target_grp:
                target_grp.visible = True
                arcpy.mapping.AddLayerToGroup(df, target_grp, layer_obj, "BOTTOM")
            else:
                arcpy.mapping.AddLayer(df, layer_obj, "TOP")

            # Garantir aplicacao direta do stretch na camada adicionada
            try:
                if tmp_lyr_file and os.path.exists(tmp_lyr_file):
                    for l_chk in arcpy.mapping.ListLayers(mxd, "", df):
                        if not l_chk.isGroupLayer and l_chk.name == layer_name:
                            arcpy.mapping.UpdateLayer(df, l_chk, arcpy.mapping.Layer(tmp_lyr_file), True)
                            break
            except Exception:
                pass

            # 6. Safety cleanup: Se inserido no grupo, remover qualquer camada que tenha
            # sido criada na raiz (onde longName == name) com o mesmo nome ou dataSource
            if target_grp:
                to_remove = []
                for lyr in arcpy.mapping.ListLayers(mxd, "", df):
                    try:
                        if not lyr.isGroupLayer and lyr.longName == lyr.name:
                            if lyr.name in suspect_names or (hasattr(lyr, 'dataSource') and os.path.normcase(lyr.dataSource) == os.path.normcase(tif_path)):
                                to_remove.append(lyr)
                    except Exception:
                        pass
                for lyr in to_remove:
                    try:
                        arcpy.mapping.RemoveLayer(df, lyr)
                    except Exception:
                        pass

            # 7. Zoom se solicitado
            if zoom:
                try:
                    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
                        if not lyr.isGroupLayer and lyr.name == layer_name:
                            df.extent = lyr.getExtent()
                            break
                except Exception:
                    pass

        finally:
            arcpy.env.addOutputsToMap = prev_add_outputs
            if prev_parallel is not None:
                try:
                    arcpy.env.parallelProcessingFactor = prev_parallel
                except Exception:
                    pass

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        # 8. Agendar cleanup diferido no proximo tick do timer (safety net contra eventos assincronos)
        global _deferred_toc_cleanup
        _deferred_toc_cleanup.append((suspect_names, group_name))

        return True, "Camada '%s' adicionada com sucesso ao grupo '%s'!" % (layer_name, group_name or "TOC")
    except Exception as e:
        return False, "Erro ao adicionar camada ao TOC: " + str(e)

def replace_in_toc(tif_path, target_long_name, new_layer_name=None, comp_code=None, sensor=None, custom_bands=None):
    """Substitui uma camada existente no TOC pela nova imagem/mosaico baixado, mantendo a posicao exata e preservando todas as bandas"""
    if not arcpy or not target_long_name:
        return False, "Alvo nao fornecido."
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]

        target_lyr = None
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            if lyr.longName == target_long_name or lyr.name == target_long_name:
                target_lyr = lyr
                break

        if not target_lyr:
            return False, "Camada alvo '%s' nao encontrada no TOC." % target_long_name

        settings = load_plugin_settings()
        cores = settings.get('multicore_cores', 4) if settings.get('multicore_enabled', True) else 1

        prev_parallel = getattr(arcpy.env, 'parallelProcessingFactor', None)
        try:
            arcpy.env.parallelProcessingFactor = str(cores)
        except Exception:
            pass

        prev_add_outputs = arcpy.env.addOutputsToMap
        arcpy.env.addOutputsToMap = False

        try:
            # 1. Estatisticas e piramides
            try:
                arcpy.CalculateStatistics_management(tif_path, 1, 1, "", "OVERWRITE")
            except Exception:
                pass
            try:
                arcpy.BuildPyramids_management(tif_path)
            except Exception:
                pass

            if not new_layer_name:
                new_layer_name = os.path.splitext(os.path.basename(tif_path))[0]

            # 2. Verificar numero de bandas
            desc = arcpy.Describe(tif_path)
            band_count = getattr(desc, 'bandCount', 1)

            temp_lyr_name = "gee_tmp_rep_" + str(abs(hash(tif_path)))[:6]
            arcpy.MakeRasterLayer_management(tif_path, temp_lyr_name)
            tmp_lyr_file = os.path.join(tempfile.gettempdir(), temp_lyr_name + ".lyr")
            try:
                if os.path.exists(tmp_lyr_file):
                    os.remove(tmp_lyr_file)
            except Exception:
                pass
            arcpy.SaveToLayerFile_management(temp_lyr_name, tmp_lyr_file)
            if band_count >= 3:
                rgb_indices = resolve_rgb_band_indices(sensor, comp_code, custom_bands, band_count)
                apply_stretch_and_stats(tmp_lyr_file, settings, rgb_bands=rgb_indices)
            else:
                apply_stretch_and_stats(tmp_lyr_file, settings, rgb_bands=None)
            new_obj = arcpy.mapping.Layer(tmp_lyr_file)

            new_obj.name = new_layer_name
            new_obj.visible = True

            arcpy.mapping.InsertLayer(df, target_lyr, new_obj, "BEFORE")
            arcpy.mapping.RemoveLayer(df, target_lyr)

            try:
                if tmp_lyr_file and os.path.exists(tmp_lyr_file):
                    for l_chk in arcpy.mapping.ListLayers(mxd, "", df):
                        if not l_chk.isGroupLayer and l_chk.name == new_layer_name:
                            arcpy.mapping.UpdateLayer(df, l_chk, arcpy.mapping.Layer(tmp_lyr_file), True)
                            break
            except Exception:
                pass
        finally:
            arcpy.env.addOutputsToMap = prev_add_outputs
            if prev_parallel is not None:
                try:
                    arcpy.env.parallelProcessingFactor = prev_parallel
                except Exception:
                    pass

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        return True, "Camada '%s' substituida por '%s' com sucesso!" % (target_long_name, new_layer_name)
    except Exception as e:
        return False, "Erro ao substituir camada no TOC: " + str(e)

def change_layer_composition(target_layer_name, composition_code, sensor):
    """Altera a composicao RGB de uma camada existente no TOC usando as bandas correspondentes sem descartar nenhuma banda"""
    if not arcpy or not target_layer_name:
        return False, "Camada alvo nao informada."
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]

        target_lyr = None
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            if lyr.longName == target_layer_name or lyr.name == target_layer_name:
                target_lyr = lyr
                break

        if not target_lyr:
            return False, "Camada '%s' nao encontrada no TOC." % target_layer_name

        data_source = target_lyr.dataSource
        if not os.path.exists(data_source):
            return False, "Arquivo raster da camada nao encontrado: " + str(data_source)

        prev_add_outputs = arcpy.env.addOutputsToMap
        arcpy.env.addOutputsToMap = False

        temp_lyr_name = "gee_temp_" + str(abs(hash(data_source + composition_code)))[:6]

        try:
            arcpy.MakeRasterLayer_management(data_source, temp_lyr_name)
            tmp_lyr_file = os.path.join(tempfile.gettempdir(), temp_lyr_name + ".lyr")
            try:
                if os.path.exists(tmp_lyr_file):
                    os.remove(tmp_lyr_file)
            except Exception:
                pass
            arcpy.SaveToLayerFile_management(temp_lyr_name, tmp_lyr_file)
            rgb_indices = resolve_rgb_band_indices(sensor, composition_code, None, band_count=None)
            apply_stretch_and_stats(tmp_lyr_file, rgb_bands=rgb_indices)

            new_obj = arcpy.mapping.Layer(tmp_lyr_file)
            new_obj.name = target_lyr.name

            arcpy.mapping.InsertLayer(df, target_lyr, new_obj, "BEFORE")
            arcpy.mapping.RemoveLayer(df, target_lyr)
        finally:
            arcpy.env.addOutputsToMap = prev_add_outputs

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        return True, "Composicao da camada '%s' alterada para '%s' com sucesso!" % (target_layer_name, composition_code)
    except Exception as e:
        return False, "Erro ao alterar composicao: " + str(e)

def apply_stretch_to_toc_layer(target_layer_name=None, settings=None):
    """Aplica e garante as configuracoes de Stretch (ex: Standard Deviations) e DRA (From Current Display Extent)
    em uma camada especifica ou em todas as camadas raster do TOC."""
    if not arcpy:
        return False, "ArcPy nao disponivel."
    if not settings:
        settings = load_plugin_settings()
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]

        rasters_to_update = []
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            if not lyr.isGroupLayer and lyr.isRasterLayer:
                if not target_layer_name or target_layer_name in ("TODAS", "Todas as camadas", "Nenhuma camada raster no TOC") or lyr.longName == target_layer_name or lyr.name == target_layer_name:
                    rasters_to_update.append(lyr)

        if not rasters_to_update:
            return False, u"Nenhuma camada raster compatível encontrada no TOC."

        prev_add = arcpy.env.addOutputsToMap
        arcpy.env.addOutputsToMap = False
        updated_count = 0
        try:
            for lyr in rasters_to_update:
                try:
                    tmp_lyr = os.path.join(tempfile.gettempdir(), "gee_stretch_" + str(abs(hash(lyr.longName)))[:6] + ".lyr")
                    if os.path.exists(tmp_lyr):
                        try: os.remove(tmp_lyr)
                        except Exception: pass
                    arcpy.SaveToLayerFile_management(lyr, tmp_lyr)
                    ok = apply_stretch_and_stats(tmp_lyr, settings)
                    if ok:
                        src_lyr = arcpy.mapping.Layer(tmp_lyr)
                        arcpy.mapping.UpdateLayer(df, lyr, src_lyr, True)
                        updated_count += 1
                except Exception as ex_item:
                    print("Erro atualizando stretch da camada %s:" % lyr.name, ex_item)
        finally:
            arcpy.env.addOutputsToMap = prev_add

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()

        st_name = settings.get('stretch_type', 'Standard Deviations')
        std_n = settings.get('stretch_std_param', 2.0)
        stats_type = settings.get('statistics_type', 'From Current Display Extent')
        return True, u"Stretch garantido em %d camada(s)! [%s (n=%.1f) | DRA: %s]" % (
            updated_count, st_name, float(std_n), stats_type
        )
    except Exception as e:
        return False, u"Erro ao garantir stretch: " + str(e)

# ==============================================================================
# PROTOCOLO DE COMUNICACAO INTER-PROCESSOS (IPC) ARCMAP <-> GUI EXTERNA
# Garante 100% de estabilidade: ArcMap NUNCA executa mainloop() e NUNCA trava
# ==============================================================================

CONTEXT_FILE = os.path.join(tempfile.gettempdir(), "gee_arcgis_context.json")
CMD_FILE = os.path.join(tempfile.gettempdir(), "gee_arcgis_cmd.json")
REPLY_FILE = os.path.join(tempfile.gettempdir(), "gee_arcgis_reply.json")

def safe_write_json(filepath, data):
    """Escreve JSON com tentativas seguras contra conflito de leitura/escrita no Windows"""
    for attempt in range(8):
        try:
            with open(filepath, "w") as f:
                json.dump(data, f)
            return True
        except Exception:
            time.sleep(0.05)
    return False

def safe_read_json(filepath):
    """Le JSON com tentativas seguras caso o arquivo esteja sendo gravado"""
    if not os.path.exists(filepath):
        return None
    for attempt in range(8):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            time.sleep(0.05)
    return None

def export_arcmap_context():
    """Exporta o contexto atual do ArcMap para arquivo JSON compartilhado"""
    if not arcpy:
        return None
    try:
        scale = get_arcmap_scale()
        bbox = get_arcmap_extent_wgs84()
        v_layers = get_arcmap_layers()
        r_layers = get_arcmap_raster_layers()
        ctx = {
            'scale': scale,
            'bbox': bbox,
            'vector_layers': v_layers,
            'raster_layers': r_layers,
            'time': time.time()
        }
        safe_write_json(CONTEXT_FILE, ctx)
        return ctx
    except Exception as e:
        print("Erro exportando contexto ArcMap:", e)
        return None

def read_arcmap_context():
    """Lido pelo processo da GUI para obter escala, camadas e extensao atuais do ArcMap"""
    return safe_read_json(CONTEXT_FILE)

_arcmap_timer_id = None
_arcmap_timer_proc = None

# Lista de cleanups diferidos: tuplas (suspect_names_set, group_name)
# Preenchida por load_into_toc; processada no proximo tick do timer
_deferred_toc_cleanup = []
_is_processing_cmd = False
_is_cleaning_toc = False

def _run_deferred_toc_cleanup():
    """Remove duplicatas de camadas na raiz do TOC agendadas pelo load_into_toc.
    Executado no proximo tick do timer, apos o ArcMap terminar de processar eventos internos.
    """
    global _deferred_toc_cleanup, _is_cleaning_toc
    if _is_cleaning_toc or not _deferred_toc_cleanup or not arcpy:
        return
    _is_cleaning_toc = True
    try:
        pending = list(_deferred_toc_cleanup)
        _deferred_toc_cleanup = []
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        changed = False
        for (suspect_names, group_name) in pending:
            # Verificar se grupo tem alguma das camadas alvo
            group_has_it = False
            for lyr in arcpy.mapping.ListLayers(mxd, "", df):
                try:
                    if not lyr.isGroupLayer and lyr.name in suspect_names:
                        if lyr.longName != lyr.name:  # esta dentro de algum grupo
                            group_has_it = True
                            break
                except Exception:
                    pass
            if not group_has_it:
                continue
            # Coletar camadas na raiz com nomes suspeitos
            to_remove = []
            for lyr in arcpy.mapping.ListLayers(mxd, "", df):
                try:
                    if not lyr.isGroupLayer and lyr.name in suspect_names:
                        if lyr.longName == lyr.name:  # camada na raiz (longName == name)
                            to_remove.append(lyr)
                except Exception:
                    pass
            for lyr in to_remove:
                try:
                    arcpy.mapping.RemoveLayer(df, lyr)
                    changed = True
                except Exception:
                    pass
        if changed:
            arcpy.RefreshTOC()
            arcpy.RefreshActiveView()
    except Exception:
        pass
    finally:
        _is_cleaning_toc = False

def start_arcmap_ipc_timer(interval_ms=500):
    """Inicia timer Win32 nativo na thread de UI do ArcMap para escutar comandos continuamente"""
    global _arcmap_timer_id, _arcmap_timer_proc
    if _arcmap_timer_id is not None:
        return True
    try:
        import ctypes
        import ctypes.wintypes
        user32 = ctypes.windll.user32
        TIMERPROC = ctypes.WINFUNCTYPE(None, ctypes.wintypes.HWND, ctypes.c_uint, ctypes.c_ulong, ctypes.wintypes.DWORD)
        def on_timer(hwnd, msg, id_event, dw_time):
            try:
                process_pending_arcmap_commands()
            except Exception:
                pass
        _timer_proc_ref = TIMERPROC(on_timer)
        t_id = user32.SetTimer(0, 0, interval_ms, _timer_proc_ref)
        if t_id != 0:
            _arcmap_timer_id = t_id
            _arcmap_timer_proc = _timer_proc_ref
            return True
    except Exception as e:
        print("Erro iniciando timer Win32:", e)
    return False

def stop_arcmap_ipc_timer():
    """Para o timer Win32 nativo do ArcMap"""
    global _arcmap_timer_id, _arcmap_timer_proc
    if _arcmap_timer_id is not None:
        try:
            import ctypes
            ctypes.windll.user32.KillTimer(0, _arcmap_timer_id)
        except Exception:
            pass
        _arcmap_timer_id = None
        _arcmap_timer_proc = None

def process_pending_arcmap_commands():
    """Executado periodicamente pelo timer nativo ou no onUpdate do Add-In (thread principal do ArcMap).
    Possui protecao estrita contra reentrancia para evitar loops de eventos COM durante RefreshTOC/RefreshActiveView.
    """
    global _is_processing_cmd
    # 1. Trava contra reentrancia: se ja estiver processando um comando, ignorar novas chamadas
    if _is_processing_cmd:
        return False

    if not os.path.exists(CMD_FILE):
        _run_deferred_toc_cleanup()
        return False

    _is_processing_cmd = True
    try:
        cmd = safe_read_json(CMD_FILE)
        # 2. CRITICO: Remover o arquivo de comando IMEDIATAMENTE antes de iniciar a execucao
        # Isso impede que eventos disparados por RefreshTOC, RefreshActiveView ou onUpdate do Add-In
        # encontrem o mesmo comando e entrem em recursao infinita!
        try:
            if os.path.exists(CMD_FILE):
                os.remove(CMD_FILE)
        except Exception:
            pass

        if not cmd:
            return False

        cmd_id = cmd.get('id', '')
        action = cmd.get('action')
        resp = {'reply_to': cmd_id, 'success': False, 'message': 'Acao desconhecida'}

        try:
            if action == 'load_layer':
                ok, msg = load_into_toc(
                    cmd['file'],
                    layer_name=cmd.get('name'),
                    group_name=cmd.get('group'),
                    zoom=cmd.get('zoom', False),
                    comp_code=cmd.get('comp'),
                    sensor=cmd.get('sensor'),
                    custom_bands=cmd.get('custom_bands')
                )
                resp = {'reply_to': cmd_id, 'success': ok, 'message': msg}
            elif action == 'replace_layer':
                ok, msg = replace_in_toc(
                    cmd['file'],
                    target_long_name=cmd['target_layer'],
                    new_layer_name=cmd.get('name'),
                    comp_code=cmd.get('comp'),
                    sensor=cmd.get('sensor'),
                    custom_bands=cmd.get('custom_bands')
                )
                resp = {'reply_to': cmd_id, 'success': ok, 'message': msg}
            elif action == 'change_composition':
                ok, msg = change_layer_composition(
                    cmd['target_layer'],
                    cmd['comp'],
                    cmd['sensor']
                )
                resp = {'reply_to': cmd_id, 'success': ok, 'message': msg}
            elif action == 'set_scale':
                ok, msg = set_arcmap_scale(cmd['scale'])
                resp = {'reply_to': cmd_id, 'success': ok, 'message': msg}
            elif action == 'export_aoi':
                tmp_geo = os.path.join(tempfile.gettempdir(), "arcgis_gee_aoi.geojson")
                buf = cmd.get('buffer_meters')
                geo_file = export_layer_to_geojson(cmd['layer_name'], tmp_geo, buffer_meters=buf)
                resp = {'reply_to': cmd_id, 'success': bool(geo_file), 'file': geo_file}
            elif action == 'refresh_context':
                ctx = export_arcmap_context()
                resp = {'reply_to': cmd_id, 'success': True, 'context': ctx}
            elif action == 'apply_stretch':
                ok, msg = apply_stretch_to_toc_layer(
                    cmd.get('layer_name'),
                    settings=cmd.get('settings')
                )
                resp = {'reply_to': cmd_id, 'success': ok, 'message': msg}
            elif action == 'eval_code':
                code_str = cmd.get('code', '')
                loc = {'result': None, 'error': None}
                try:
                    exec(code_str, globals(), loc)
                    resp = {'reply_to': cmd_id, 'success': True, 'result': repr(loc.get('result'))}
                except Exception as ex:
                    import traceback
                    resp = {'reply_to': cmd_id, 'success': False, 'message': unicode(ex) + u"\n" + unicode(traceback.format_exc())}
        except Exception as ex:
            import traceback
            resp = {'reply_to': cmd_id, 'success': False, 'message': unicode(ex) + u"\n" + unicode(traceback.format_exc())}

        # Gravar resposta com safe_write_json
        safe_write_json(REPLY_FILE, resp)

        # Atualizar contexto apos alteracoes
        try:
            export_arcmap_context()
        except Exception:
            pass

        # Processar cleanups pendentes
        _run_deferred_toc_cleanup()

        return True

    finally:
        # Liberar a trava sob qualquer circunstancia
        _is_processing_cmd = False

def send_arcmap_command(action_dict, timeout=120):
    """Envia um comando para o ArcMap a partir do processo da GUI e aguarda a confirmacao"""
    cmd_id = "cmd_" + str(int(time.time() * 1000))
    action_dict['id'] = cmd_id

    # Limpar resposta anterior se existir
    if os.path.exists(REPLY_FILE):
        try:
            os.remove(REPLY_FILE)
        except Exception:
            pass

    # Escrever arquivo de comando com safe_write_json
    safe_write_json(CMD_FILE, action_dict)

    # Aguardar resposta no arquivo REPLY_FILE
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(REPLY_FILE):
            rep = safe_read_json(REPLY_FILE)
            if rep and rep.get('reply_to') == cmd_id:
                try:
                    os.remove(REPLY_FILE)
                except Exception:
                    pass
                return rep
        time.sleep(0.2)

    # Limpar comando pendente para evitar bloqueios ou execucoes tardias
    try:
        if os.path.exists(CMD_FILE):
            os.remove(CMD_FILE)
    except Exception:
        pass

    return {'success': False, 'message': u'Tempo limite esgotado (%ds) aguardando resposta do ArcMap.' % timeout}

def apply_stretch(layer_name=None, settings=None):
    """Envia comando para o ArcMap aplicar/garantir o Stretch configurado na camada ou no mapa"""
    return send_arcmap_command({
        'action': 'apply_stretch',
        'layer_name': layer_name,
        'settings': settings
    })

def launch_gui_process():
    """Inicia a interface grafica como processo independente pythonw.exe sem travar o ArcMap"""
    pyw = r"C:\Python27\ArcGIS10.8\pythonw.exe"
    if not os.path.exists(pyw):
        pyw = "pythonw.exe"

    install_dir = os.path.dirname(os.path.abspath(__file__))
    gui_script = os.path.join(install_dir, "gee_gui.py")

    # Iniciar timer IPC de background no ArcMap (a cada 500ms)
    start_arcmap_ipc_timer(500)

    # Exportar contexto antes de abrir a janela
    export_arcmap_context()

    clean_env = dict(os.environ)
    clean_env.pop('PYTHONPATH', None)
    clean_env.pop('PYTHONHOME', None)

    try:
        subprocess.Popen([pyw, gui_script], cwd=install_dir, env=clean_env)
        return True, "GUI iniciada com sucesso em processo separado."
    except Exception as e:
        return False, str(e)
