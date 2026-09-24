# -*- coding: utf-8 -*-
"""
Script para empacotar o Python Add-In do ArcGIS (.esriaddin)
"""

import os
import sys
import zipfile

def make_addin():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_zip_name = os.path.join(current_dir, "GEE_Image_Selector.esriaddin")

    print("Gerando pacote Add-In: %s" % out_zip_name)
    if os.path.exists(out_zip_name):
        try:
            os.remove(out_zip_name)
        except Exception:
            pass

    with zipfile.ZipFile(out_zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
        # 1. config.xml
        cfg_file = os.path.join(current_dir, "config.xml")
        if os.path.exists(cfg_file):
            z.write(cfg_file, "config.xml")

        # 2. Pasta Install
        install_dir = os.path.join(current_dir, "Install")
        for root, dirs, files in os.walk(install_dir):
            for f in files:
                if f.endswith('.pyc') or f.endswith('.pyo'):
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, current_dir)
                z.write(full_path, rel_path)

        # 3. Pasta Images
        images_dir = os.path.join(current_dir, "Images")
        for root, dirs, files in os.walk(images_dir):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, current_dir)
                z.write(full_path, rel_path)

    print("Pacote .esriaddin gerado com sucesso!")
    return out_zip_name

if __name__ == "__main__":
    make_addin()
