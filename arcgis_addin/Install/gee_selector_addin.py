# -*- coding: utf-8 -*-
"""
Python Add-In para ArcMap 10.8.2
GEE Image Selector
"""

import sys
import os

# Garantir que a pasta Install esta no path
install_dir = os.path.dirname(os.path.abspath(__file__))
if install_dir not in sys.path:
    sys.path.insert(0, install_dir)

try:
    import arcpy
    import pythonaddins
except ImportError:
    pass

class OpenGEESelectorButton(object):
    """Implementacao do botao na Toolbar do ArcMap"""
    def __init__(self):
        self.enabled = True
        self.checked = False
        self._last_ctx_time = 0
        try:
            import gee_bridge
            try:
                reload(gee_bridge)
            except Exception:
                pass
            gee_bridge.start_arcmap_ipc_timer(500)
            gee_bridge.export_arcmap_context()
        except Exception:
            pass

    def onClick(self):
        try:
            import gee_bridge
            try:
                reload(gee_bridge)
            except Exception:
                pass
            gee_bridge.start_arcmap_ipc_timer(500)
            gee_bridge.export_arcmap_context()
            ok, msg = gee_bridge.launch_gui_process()
            if not ok:
                pythonaddins.MessageBox(u"Falha ao iniciar processo da interface:\n" + unicode(msg), "Erro", 0)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            try:
                pythonaddins.MessageBox(u"Erro ao abrir Seletor GEE:\n" + unicode(e) + u"\n\n" + unicode(tb), "Erro", 0)
            except Exception:
                print("Erro:", tb)

    def onUpdate(self):
        try:
            import gee_bridge
            # 1. Se o ArcMap ja estiver processando um comando, nao reentrar
            if getattr(gee_bridge, '_is_processing_cmd', False):
                return

            # 2. Processar acoes pendentes enviadas pela GUI somente se houver comando no disco
            if os.path.exists(gee_bridge.CMD_FILE):
                gee_bridge.process_pending_arcmap_commands()

            # 3. Atualizar contexto da tela periodicamente (a cada 3s) para manter escala da GUI atualizada
            import time
            now = time.time()
            if now - self._last_ctx_time > 3.0:
                self._last_ctx_time = now
                gee_bridge.export_arcmap_context()
        except Exception:
            pass
