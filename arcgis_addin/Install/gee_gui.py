# -*- coding: utf-8 -*-
"""
Interface Grafica (GUI) para ArcMap 10.8.2
Foco: Estabilidade total, processo independente via IPC, zero risco de crash no ArcMap.
Recursos:
- Execucao em processo proprio (pythonw.exe) sem travar o ArcMap
- Selecao multipla de imagens (selectmode extended)
- Download e carregamento em segundo plano (background) com atualizacao no TOC
- Suporte a Multibanda completa (todas as bandas brutas) ou RGB Rapido
- Mapeamento e substituicao de camadas existentes no TOC
- Controle e validacao da escala maxima 1:500.000
- Miniaturas sob medida com abertura no navegador
"""

import os
import sys
import tempfile
import threading
import datetime
import webbrowser
import time
import multiprocessing
try:
    import concurrent.futures
except ImportError:
    concurrent = None

# Compatibilidade Python 2.7 e Python 3
if sys.version_info[0] < 3:
    import Tkinter as tk
    import ttk
    import tkMessageBox as messagebox
    import tkSimpleDialog as simpledialog
    import tkFileDialog as filedialog
    import Queue as queue_mod
else:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
    from tkinter import simpledialog
    from tkinter import filedialog
    import queue as queue_mod

import gee_bridge

def get_icon_path(filename="app_icon.ico"):
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(curr_dir, filename),
        os.path.join(curr_dir, "Images", filename),
        os.path.join(curr_dir, "..", "Images", filename),
        os.path.join(r"C:\Users\joberthgambati\.gemini\antigravity\scratch\gee_arcgis_plugin\arcgis_addin\Images", filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None

def get_tk_image(base_name):
    """Retorna PhotoImage compativel com Tkinter (prioriza .gif para suporte a Tcl/Tk 8.5 no Python 2.7)"""
    for ext in [".gif", ".png"]:
        p = get_icon_path(base_name + ext)
        if p and os.path.exists(p):
            try:
                return tk.PhotoImage(file=p)
            except Exception:
                pass
    return None

def setup_window_icon(window):
    """Aplica o ícone oficial da ferramenta na barra de título e barra de tarefas do Windows"""
    ico_p = get_icon_path("app_icon.ico")
    if ico_p:
        try:
            window.iconbitmap(default=ico_p)
            return
        except Exception:
            try:
                window.iconbitmap(ico_p)
                return
            except Exception:
                pass

    for name in ["icon32", "icon24", "icon16", "icon"]:
        img = get_tk_image(name)
        if img:
            try:
                window.iconphoto(True, img)
                window._icon_photo_ref = img
                return
            except Exception:
                pass

class GEESettingsDialog(object):
    """Janela modal para configuracao de Stretch, Estatisticas (DRA) e Multicore"""
    def __init__(self, parent):
        self.parent = parent
        p_win = parent.root if hasattr(parent, 'root') else parent
        self.top = tk.Toplevel(p_win)
        self.top.title(u"Configurações - CGMA ArcGEE Explorer")
        self.top.geometry("540x690")
        self.top.resizable(False, False)
        setup_window_icon(self.top)
        self.top.transient(p_win)
        self.top.grab_set()

        # Centralizar na janela pai
        try:
            x = p_win.winfo_rootx() + (p_win.winfo_width() // 2) - 270
            y = p_win.winfo_rooty() + (p_win.winfo_height() // 2) - 335
            self.top.geometry("+%d+%d" % (max(0, x), max(0, y)))
        except Exception:
            pass

        # Detectar CPU cores
        try:
            self.max_system_cores = multiprocessing.cpu_count()
        except Exception:
            self.max_system_cores = 4

        # Carregar configuracoes salvas
        self.settings = gee_bridge.load_plugin_settings()

        self.setup_ui()

    def setup_ui(self):
        main_pad = ttk.Frame(self.top, padding=12)
        main_pad.pack(fill=tk.BOTH, expand=True)

        # 1. Grupo Stretch (Realce)
        grp_stretch = ttk.LabelFrame(main_pad, text=u" Realce de Contraste Padrão (Stretch) ", padding=10)
        grp_stretch.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(grp_stretch, text=u"Tipo de Stretch:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.var_stretch = tk.StringVar(value=self.settings.get('stretch_type', 'Standard Deviations'))
        self.cbo_stretch = ttk.Combobox(
            grp_stretch,
            textvariable=self.var_stretch,
            state="readonly",
            values=[
                "Standard Deviations",
                "Percent Clip",
                "Minimum-Maximum",
                "Histogram Equalize",
                "None",
                "Esri",
                "Sigmoid"
            ],
            width=24
        )
        self.cbo_stretch.grid(row=0, column=1, sticky=tk.W, padx=8, pady=4)
        self.cbo_stretch.bind("<<ComboboxSelected>>", self._on_stretch_changed)

        ttk.Label(grp_stretch, text=u"Desvios Padrão (n):").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.var_std_param = tk.DoubleVar(value=float(self.settings.get('stretch_std_param', 2.0)))
        self.spn_std = tk.Spinbox(
            grp_stretch,
            from_=0.5,
            to=5.0,
            increment=0.5,
            textvariable=self.var_std_param,
            width=8
        )
        self.spn_std.grid(row=1, column=1, sticky=tk.W, padx=8, pady=4)
        self.lbl_std_hint = ttk.Label(grp_stretch, text=u"(Padrão recomendado: 2.0)", font=("Segoe UI", 8), foreground="#555")
        self.lbl_std_hint.grid(row=1, column=1, sticky=tk.W, padx=(85, 0), pady=4)

        btn_apply_now = ttk.Button(
            grp_stretch,
            text=u"⚡ Aplicar e Garantir Stretch Atual nas Camadas do ArcMap",
            command=self.on_apply_stretch_now
        )
        btn_apply_now.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 2))

        # 2. Grupo Estatisticas (DRA)
        grp_stats = ttk.LabelFrame(main_pad, text=u" Cálculo de Estatísticas do Raster (DRA) ", padding=10)
        grp_stats.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(grp_stats, text=u"Origem das Estatísticas:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.var_stats = tk.StringVar(value=self.settings.get('statistics_type', 'From Current Display Extent'))
        self.cbo_stats = ttk.Combobox(
            grp_stats,
            textvariable=self.var_stats,
            state="readonly",
            values=[
                "From Current Display Extent",
                "From Each Raster Dataset",
                "From Custom Settings"
            ],
            width=28
        )
        self.cbo_stats.grid(row=0, column=1, sticky=tk.W, padx=8, pady=4)

        lbl_stats_desc = ttk.Label(
            grp_stats,
            text=u"• 'From Current Display Extent' (DRA) adapta o contraste dinamicamente\n  à extensão visível na tela para nitidez ideal das bandas.",
            font=("Segoe UI", 8),
            foreground="#1b4f72"
        )
        lbl_stats_desc.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        # 3. Grupo Multicore
        grp_multi = ttk.LabelFrame(main_pad, text=u" Desempenho e Aceleração Multicore ", padding=10)
        grp_multi.pack(fill=tk.X, pady=(0, 12))

        self.var_multicore = tk.BooleanVar(value=bool(self.settings.get('multicore_enabled', True)))
        self.chk_multi = ttk.Checkbutton(
            grp_multi,
            text=u"Ativar processamento e downloads paralelos Multicore",
            variable=self.var_multicore,
            command=self._on_multi_toggled
        )
        self.chk_multi.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(grp_multi, text=u"Número de Cores (Threads):").grid(row=1, column=0, sticky=tk.W, pady=4)
        init_cores = int(self.settings.get('multicore_cores', min(4, self.max_system_cores)))
        self.var_cores = tk.IntVar(value=min(max(1, init_cores), self.max_system_cores))
        self.spn_cores = tk.Spinbox(
            grp_multi,
            from_=1,
            to=self.max_system_cores,
            increment=1,
            textvariable=self.var_cores,
            width=8
        )
        self.spn_cores.grid(row=1, column=1, sticky=tk.W, padx=8, pady=4)

        lbl_cores_hint = ttk.Label(
            grp_multi,
            text=u"(Detectados: %d núcleos na CPU)" % self.max_system_cores,
            font=("Segoe UI", 8),
            foreground="#555"
        )
        lbl_cores_hint.grid(row=1, column=1, sticky=tk.W, padx=(85, 0), pady=4)

        lbl_multi_desc = ttk.Label(
            grp_multi,
            text=u"• Acelera a geração de pirâmides e cálculo de estatísticas no ArcMap.\n• Permite o download simultâneo de múltiplas cenas em segundo plano.",
            font=("Segoe UI", 8),
            foreground="#0b5345"
        )
        lbl_multi_desc.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        # 4. Grupo Buffer da Camada Vetorial (AOI)
        grp_aoi = ttk.LabelFrame(main_pad, text=u" Buffer do Retângulo Envolvente (AOI) ", padding=10)
        grp_aoi.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(grp_aoi, text=u"Buffer Adicional (metros):").grid(row=0, column=0, sticky=tk.W, pady=4)
        init_buffer = float(self.settings.get('aoi_buffer_meters', 1000.0))
        self.var_aoi_buffer = tk.DoubleVar(value=init_buffer)
        self.spn_aoi_buffer = tk.Spinbox(
            grp_aoi,
            from_=0,
            to=50000,
            increment=100,
            textvariable=self.var_aoi_buffer,
            width=10
        )
        self.spn_aoi_buffer.grid(row=0, column=1, sticky=tk.W, padx=8, pady=4)

        lbl_buffer_hint = ttk.Label(
            grp_aoi,
            text=u"(Padrão: 1000m = 1 km | ex: 0m, 500m, 1000m, 2000m)",
            font=("Segoe UI", 8),
            foreground="#555"
        )
        lbl_buffer_hint.grid(row=0, column=1, sticky=tk.W, padx=(100, 0), pady=4)

        lbl_aoi_desc = ttk.Label(
            grp_aoi,
            text=u"• Expande o retângulo envolvente da AOI em N metros em todas as direções\n  para garantir margem de contexto geográfico no raster exportado.",
            font=("Segoe UI", 8),
            foreground="#1b4f72"
        )
        lbl_aoi_desc.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        # 5. Grupo Atualização do Plugin
        grp_update = ttk.LabelFrame(main_pad, text=u" Atualização do Plugin ", padding=10)
        grp_update.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            grp_update,
            text=u"Sincronize o plugin com as últimas melhorias via GitHub ou arquivo ZIP local:",
            font=("Segoe UI", 8),
            foreground="#333"
        ).pack(anchor=tk.W, pady=(0, 6))

        btn_open_updater = ttk.Button(
            grp_update,
            text=u"🔄 Abrir Assistente de Atualização (GitHub / ZIP)",
            command=self._open_updater
        )
        btn_open_updater.pack(anchor=tk.W)

        # 6. Barra de Botoes
        btn_bar = ttk.Frame(main_pad)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))

        btn_defaults = ttk.Button(btn_bar, text=u"Restaurar Padrões", command=self.on_restore_defaults)
        btn_defaults.pack(side=tk.LEFT)

        btn_cancel = ttk.Button(btn_bar, text=u"Cancelar", command=self.top.destroy)
        btn_cancel.pack(side=tk.RIGHT, padx=(6, 0))

        btn_save = ttk.Button(btn_bar, text=u"Salvar Configurações", style="Primary.TButton", command=self.on_save)
        btn_save.pack(side=tk.RIGHT)

        self._on_stretch_changed()
        self._on_multi_toggled()

    def _open_updater(self):
        GEEUpdaterDialog(self.parent)

    def _on_stretch_changed(self, event=None):
        st = self.var_stretch.get()
        if st in ("Standard Deviations", "Standard Deviation"):
            self.spn_std.config(state=tk.NORMAL)
            self.lbl_std_hint.config(foreground="#555")
        else:
            self.spn_std.config(state=tk.DISABLED)
            self.lbl_std_hint.config(foreground="#aaa")

    def _on_multi_toggled(self):
        if self.var_multicore.get():
            self.spn_cores.config(state=tk.NORMAL)
        else:
            self.spn_cores.config(state=tk.DISABLED)

    def on_restore_defaults(self):
        self.var_stretch.set("Standard Deviations")
        self.var_std_param.set(2.0)
        self.var_stats.set("From Current Display Extent")
        self.var_multicore.set(True)
        self.var_cores.set(min(4, self.max_system_cores))
        self.var_aoi_buffer.set(1000.0)
        self._on_stretch_changed()
        self._on_multi_toggled()

    def on_apply_stretch_now(self):
        new_settings = {
            'stretch_type': self.var_stretch.get(),
            'stretch_std_param': float(self.var_std_param.get()),
            'statistics_type': self.var_stats.get(),
            'multicore_enabled': bool(self.var_multicore.get()),
            'multicore_cores': int(self.var_cores.get()),
            'aoi_buffer_meters': float(self.var_aoi_buffer.get())
        }
        gee_bridge.save_plugin_settings(new_settings)
        if hasattr(self.parent, 'settings'):
            self.parent.settings = new_settings

        rep = gee_bridge.apply_stretch(None, settings=new_settings)
        if rep.get('success'):
            messagebox.showinfo(u"Stretch Garantido", rep.get('message', u"Stretch aplicado com sucesso!"), parent=self.top)
        else:
            messagebox.showwarning(u"Aviso ArcMap", rep.get('message', u"Não foi possível aplicar nas camadas do TOC."), parent=self.top)

    def on_save(self):
        new_settings = {
            'stretch_type': self.var_stretch.get(),
            'stretch_std_param': float(self.var_std_param.get()),
            'statistics_type': self.var_stats.get(),
            'multicore_enabled': bool(self.var_multicore.get()),
            'multicore_cores': int(self.var_cores.get()),
            'aoi_buffer_meters': float(self.var_aoi_buffer.get())
        }
        if gee_bridge.save_plugin_settings(new_settings):
            if hasattr(self.parent, 'settings'):
                self.parent.settings = new_settings
            messagebox.showinfo(u"Configurações Salvas", u"As preferências de Stretch, Estatísticas, Multicore e Buffer de AOI foram salvas com sucesso!", parent=self.top)
            self.top.destroy()
        else:
            messagebox.showerror(u"Erro", u"Falha ao salvar arquivo de configurações.", parent=self.top)

class GEEAboutDialog(object):
    """Janela modal Sobre com informações institucionais, versão, links e dicas"""
    def __init__(self, parent):
        self.parent = parent
        p_win = parent.root if hasattr(parent, 'root') else parent
        self.top = tk.Toplevel(p_win)
        self.top.title(u"Sobre - CGMA ArcGEE Explorer")
        self.top.geometry("580x525")
        self.top.resizable(False, False)
        setup_window_icon(self.top)
        self.top.transient(p_win)
        self.top.grab_set()

        try:
            x = p_win.winfo_rootx() + (p_win.winfo_width() // 2) - 290
            y = p_win.winfo_rooty() + (p_win.winfo_height() // 2) - 262
            self.top.geometry("+%d+%d" % (max(0, x), max(0, y)))
        except Exception:
            pass

        pad = ttk.Frame(self.top, padding=16)
        pad.pack(fill=tk.BOTH, expand=True)

        head_frame = ttk.Frame(pad)
        head_frame.pack(fill=tk.X, pady=(0, 10))

        # Logo em destaque de alta definicao no dialogo Sobre
        self.about_photo = get_tk_image("about_logo") or get_tk_image("icon64") or get_tk_image("icon")
        if self.about_photo:
            lbl_about_ico = ttk.Label(head_frame, image=self.about_photo)
            lbl_about_ico.pack(side=tk.LEFT, padx=(0, 16))

        title_box = ttk.Frame(head_frame)
        title_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        lbl_title = tk.Label(
            title_box,
            text=u"CGMA ArcGEE Explorer",
            font=("Segoe UI", 16, "bold"),
            fg="#0b5345"
        )
        lbl_title.pack(anchor=tk.W, pady=(4, 2))

        lbl_sub = tk.Label(
            title_box,
            text=u"Google Earth Engine Explorer for ArcGIS Desktop 10.8 (ArcMap)  |  v1.4",
            font=("Segoe UI", 9, "italic"),
            fg="#566573"
        )
        lbl_sub.pack(anchor=tk.W, pady=(0, 4))

        lbl_tag = tk.Label(
            title_box,
            text=u"Sensoriamento Remoto & Observação da Terra com Qualidade Nativa 100%",
            font=("Segoe UI", 8, "bold"),
            fg="#1b4f72"
        )
        lbl_tag.pack(anchor=tk.W)

        sep1 = ttk.Separator(pad, orient=tk.HORIZONTAL)
        sep1.pack(fill=tk.X, pady=(0, 10))

        info_frame = ttk.LabelFrame(pad, text=u" Informações do Sistema ", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        info_text = (
            u"• Versão: v1.4 (Garantia Estrita de Qualidade Nativa 100%)\n"
            u"• Organização: Coordenadoria de Geoprocessamento e Monitoramento Ambiental\n"
            u"  Secretaria de Estado de Meio Ambiente de Mato Grosso (CGMA / SEMA-MT)\n"
            u"• Desenvolvedor: Joberth Firmino Gambati\n"
            u"• Compatibilidade: ArcGIS Desktop 10.8 / 10.8.2 (ArcMap) & Python 3.9+\n"
            u"• Licença: Código Aberto (MIT License)"
        )
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)

        tips_frame = ttk.LabelFrame(pad, text=u" Dicas Rápidas de Operação ", padding=10)
        tips_frame.pack(fill=tk.X, pady=(0, 12))

        tips_text = (
            u"1. Resolução Nativa: Sentinel-2 (10m) e Landsat (30m) sem qualquer perda.\n"
            u"2. Limite GEE 48 MB: Para Sentinel-2, utilize zoom <= 1:250.000 ou Camada (AOI).\n"
            u"3. Buffer de AOI: Ajuste em 'Configurações' a margem em metros ao redor do vetor.\n"
            u"4. Simbologia e Bandas: Altere as bandas RGB no TOC diretamente com botão direito."
        )
        ttk.Label(tips_frame, text=tips_text, justify=tk.LEFT).pack(anchor=tk.W)

        btn_bar = ttk.Frame(pad)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn_gh = ttk.Button(btn_bar, text=u"🌐 Abrir Repositório no GitHub", command=self._open_github)
        btn_gh.pack(side=tk.LEFT)

        btn_close = ttk.Button(btn_bar, text=u"Fechar", command=self.top.destroy)
        btn_close.pack(side=tk.RIGHT)

    def _open_github(self):
        try:
            webbrowser.open("https://github.com/Yiuky/CGMA-ARCGIS-GEE-PLUGIN")
        except Exception:
            pass

def safe_makedirs(path):
    if not path:
        return
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise

class GEEUpdaterDialog(object):
    """Janela modal para atualização automática do plugin via GitHub ou arquivo ZIP"""
    def __init__(self, parent):
        self.parent = parent
        self.top = tk.Toplevel(parent.root if hasattr(parent, 'root') else parent)
        self.top.title(u"Atualizar - CGMA ArcGEE Explorer")
        self.top.geometry("540x380")
        self.top.resizable(False, False)
        setup_window_icon(self.top)
        self.top.transient(parent.root if hasattr(parent, 'root') else parent)
        self.top.grab_set()

        try:
            p_win = parent.root if hasattr(parent, 'root') else parent
            x = p_win.winfo_rootx() + (p_win.winfo_width() // 2) - 270
            y = p_win.winfo_rooty() + (p_win.winfo_height() // 2) - 190
            self.top.geometry("+%d+%d" % (max(0, x), max(0, y)))
        except Exception:
            pass

        pad = ttk.Frame(self.top, padding=16)
        pad.pack(fill=tk.BOTH, expand=True)

        lbl_head = tk.Label(
            pad,
            text=u"Atualização do CGMA ArcGEE Explorer",
            font=("Segoe UI", 12, "bold"),
            fg="#1b4f72"
        )
        lbl_head.pack(anchor=tk.W, pady=(0, 6))

        lbl_desc = ttk.Label(
            pad,
            text=u"Escolha o método desejado para atualizar o plugin e seus componentes:"
        )
        lbl_desc.pack(anchor=tk.W, pady=(0, 10))

        box_git = ttk.LabelFrame(pad, text=u" Método 1: Atualizar Diretamente via GitHub (Online) ", padding=10)
        box_git.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            box_git,
            text=u"Baixa as alterações mais recentes do repositório oficial no GitHub,\nrecompila o Add-In e atualiza o AssemblyCache do ArcMap."
        ).pack(anchor=tk.W, pady=(0, 6))

        self.btn_git_update = ttk.Button(box_git, text=u"⬇ Atualizar pelo GitHub Agora", command=self._do_github_update)
        self.btn_git_update.pack(anchor=tk.W)

        box_zip = ttk.LabelFrame(pad, text=u" Método 2: Atualizar a partir de Arquivo ZIP Local ", padding=10)
        box_zip.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            box_zip,
            text=u"Selecione um arquivo .zip com a nova versão do plugin para instalar offline."
        ).pack(anchor=tk.W, pady=(0, 6))

        self.btn_zip_update = ttk.Button(box_zip, text=u"📂 Selecionar Arquivo ZIP e Atualizar", command=self._do_zip_update)
        self.btn_zip_update.pack(anchor=tk.W)

        self.lbl_status = ttk.Label(pad, text=u"Pronto para atualizar.", font=("Segoe UI", 8), foreground="#555")
        self.lbl_status.pack(anchor=tk.W, pady=(0, 6))

        btn_close = ttk.Button(pad, text=u"Fechar", command=self.top.destroy)
        btn_close.pack(side=tk.RIGHT)

    def _get_plugin_root(self):
        curr = os.path.dirname(os.path.abspath(__file__))
        p = os.path.abspath(os.path.join(curr, "..", ".."))
        if os.path.exists(os.path.join(p, "arcgis_addin")):
            return p
        return curr

    def _redeploy_plugin(self, root_dir):
        make_script = os.path.join(root_dir, "arcgis_addin", "makeaddin.py")
        if os.path.exists(make_script):
            import subprocess
            py_exe = sys.executable
            subprocess.call([py_exe, make_script], cwd=root_dir)

        addin_src = os.path.join(root_dir, "arcgis_addin", "GEE_Image_Selector.esriaddin")
        user_prof = os.environ.get('USERPROFILE', '')
        addin_dest = os.path.join(user_prof, r"Documents\ArcGIS\AddIns\Desktop10.8\{ceae58c4-c44e-4edd-b8f4-1ba7d13b6b7d}\GEE_Image_Selector.esriaddin")
        cache_dir = os.path.join(user_prof, r"AppData\Local\ESRI\Desktop10.8\AssemblyCache\{CEAE58C4-C44E-4EDD-B8F4-1BA7D13B6B7D}")
        install_src = os.path.join(root_dir, "arcgis_addin", "Install")

        import shutil
        if os.path.exists(addin_src) and os.path.exists(os.path.dirname(addin_dest)):
            try: shutil.copy2(addin_src, addin_dest)
            except Exception: pass

        if os.path.exists(cache_dir) and os.path.exists(install_src):
            for item in os.listdir(install_src):
                s = os.path.join(install_src, item)
                d = os.path.join(cache_dir, item)
                try:
                    if os.path.isdir(s):
                        if os.path.exists(d): shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                except Exception:
                    pass

    def _do_github_update(self):
        self.lbl_status.config(text=u"Conectando ao GitHub para baixar atualizações...")
        self.btn_git_update.config(state=tk.DISABLED)

        def worker():
            root_dir = self._get_plugin_root()
            success = False
            msg = ""
            try:
                git_dir = os.path.join(root_dir, ".git")
                if os.path.exists(git_dir):
                    import subprocess
                    r = subprocess.call(["git", "pull", "origin", "main"], cwd=root_dir)
                    if r == 0:
                        success = True
                        msg = u"Repositório sincronizado via Git com sucesso!"

                if not success:
                    import urllib
                    zip_url = "https://github.com/Yiuky/CGMA-ARCGIS-GEE-PLUGIN/archive/refs/heads/main.zip"
                    tmp_zip = os.path.join(tempfile.gettempdir(), "gee_plugin_update.zip")
                    try:
                        if sys.version_info[0] < 3:
                            urllib.urlretrieve(zip_url, tmp_zip)
                        else:
                            import urllib.request
                            urllib.request.urlretrieve(zip_url, tmp_zip)

                        import zipfile
                        with zipfile.ZipFile(tmp_zip, 'r') as z:
                            for member in z.infolist():
                                parts = member.filename.split('/', 1)
                                if len(parts) > 1 and parts[1]:
                                    target_p = os.path.join(root_dir, parts[1])
                                    is_dir = member.filename.endswith('/') or member.filename.endswith('\\')
                                    if is_dir:
                                        safe_makedirs(target_p)
                                    else:
                                        parent_p = os.path.dirname(target_p)
                                        if parent_p:
                                            safe_makedirs(parent_p)
                                        data = z.read(member.filename)
                                        with open(target_p, 'wb') as dst:
                                            dst.write(data)
                        success = True
                        msg = u"Código mais recente baixado e extraído do GitHub com sucesso!"
                    except Exception as ex_dl:
                        msg = u"Erro ao baixar do GitHub: " + str(ex_dl)

                if success:
                    self._redeploy_plugin(root_dir)

                def show_result():
                    self.btn_git_update.config(state=tk.NORMAL)
                    if success:
                        self.lbl_status.config(text=u"Atualização concluída com sucesso!")
                        messagebox.showinfo(
                            u"Atualização Concluída",
                            u"%s\n\nO Add-In e o AssemblyCache foram recompilados.\nReabra o Seletor GEE ou reinicie o ArcMap para aplicar as alterações." % msg,
                            parent=self.top
                        )
                        self.top.destroy()
                    else:
                        self.lbl_status.config(text=u"Falha na atualização.")
                        messagebox.showerror(u"Erro na Atualização", msg, parent=self.top)

                if hasattr(self.parent, 'post_to_gui'):
                    self.parent.post_to_gui(show_result)
                else:
                    self.top.after(0, show_result)
            except Exception as e:
                err_text = str(e)
                def on_err():
                    self.btn_git_update.config(state=tk.NORMAL)
                    messagebox.showerror(u"Erro Inesperado", err_text, parent=self.top)
                self.top.after(0, on_err)

        threading.Thread(target=worker).start()

    def _do_zip_update(self):
        zip_path = filedialog.askopenfilename(
            title=u"Selecione o arquivo ZIP de atualização do Plugin",
            filetypes=[("Arquivos ZIP (*.zip)", "*.zip")],
            parent=self.top
        )
        if not zip_path or not os.path.exists(zip_path):
            return

        self.lbl_status.config(text=u"Extraindo pacote ZIP selecionado...")
        root_dir = self._get_plugin_root()

        try:
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as z:
                has_root_prefix = False
                names = z.namelist()
                if names and '/' in names[0]:
                    first_dir = names[0].split('/')[0]
                    if all(n.startswith(first_dir + '/') for n in names if n != first_dir + '/'):
                        has_root_prefix = True

                for member in z.infolist():
                    if has_root_prefix:
                        parts = member.filename.split('/', 1)
                        if len(parts) > 1 and parts[1]:
                            rel_name = parts[1]
                        else:
                            continue
                    else:
                        rel_name = member.filename

                    if not rel_name:
                        continue
                    target_p = os.path.join(root_dir, rel_name)
                    is_dir = member.filename.endswith('/') or member.filename.endswith('\\')
                    if is_dir:
                        safe_makedirs(target_p)
                    else:
                        parent_p = os.path.dirname(target_p)
                        if parent_p:
                            safe_makedirs(parent_p)
                        data = z.read(member.filename)
                        with open(target_p, 'wb') as dst:
                            dst.write(data)

            self._redeploy_plugin(root_dir)
            self.lbl_status.config(text=u"Atualização via ZIP concluída com sucesso!")
            messagebox.showinfo(
                u"Atualização Concluída",
                u"O pacote ZIP foi aplicado e o Add-In recompilado com sucesso!\n\nReabra a ferramenta para carregar a nova versão.",
                parent=self.top
            )
            self.top.destroy()
        except Exception as e:
            messagebox.showerror(u"Erro ao Extrair ZIP", str(e), parent=self.top)

SENSOR_DISPLAY = [
    ("Sentinel-2 (Harmonized)", "S2"),
    ("Landsat 8 (Collection 2 - L2)", "L8"),
    ("Landsat 7 (Collection 2 - L2)", "L7"),
    ("Landsat 5 (Collection 2 - L2)", "L5"),
    ("Landsat 4 (Collection 2 - L2)", "L4"),
    ("Landsat 3 (Collection 1 - MSS)", "L3"),
    ("Landsat 2 (Collection 1 - MSS)", "L2"),
    ("Landsat 1 (Collection 1 - MSS)", "L1")
]

MAX_ALLOWED_SCALE = 500000.0

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

class GEEPluginWindow(object):
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(u"CGMA ArcGEE Explorer (ArcGIS 10.8)  |  v1.4")
        self.root.geometry("1100x740")
        self.root.minsize(960, 640)
        setup_window_icon(self.root)

        # Interceptar fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Fila de comunicacao interna da GUI
        self.queue = queue_mod.Queue()
        self._alive = True
        self.arcmap_context = {}

        # Configuracao visual ttk
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        self.style.configure("TLabel", font=("Segoe UI", 9))
        self.style.configure("TButton", font=("Segoe UI", 9))
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), foreground="#0b5345")
        self.style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), foreground="#1a5276")

        self.thumb_photo = None
        self.current_thumb_url = None
        self.is_authenticated = False
        self.images_cache = []
        self.is_downloading = False
        self.settings = gee_bridge.load_plugin_settings()

        self.setup_ui()
        self.populate_initial_data()

        # Iniciar verificacoes em segundo plano de forma diferida
        self.root.after(100, self._deferred_init)

    def on_close(self):
        """Encerra o processo da GUI de forma limpa"""
        try:
            self._alive = False
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def post_to_gui(self, callback):
        """Envia uma acao para ser executada na thread principal do Tkinter"""
        if self._alive:
            self.queue.put(callback)

    def _schedule_poll(self):
        if self._alive:
            self.root.after(100, self._process_queue)

    def _process_queue(self):
        """Processa mensagens internas da fila de tarefas"""
        if not self._alive:
            return
        try:
            while True:
                cb = self.queue.get_nowait()
                try:
                    cb()
                except Exception as e:
                    print("Erro executando item da fila:", e)
        except queue_mod.Empty:
            pass
        except Exception:
            pass

        if self._alive:
            self._schedule_poll()

    def _deferred_init(self):
        self._schedule_poll()
        self.sync_arcmap_context()
        self.async_check_gee()
        self.root.after(2000, self._poll_arcmap_context)

    def _poll_arcmap_context(self):
        """Sincroniza periodicamente com o contexto do ArcMap (escala, camadas)"""
        if not self._alive:
            return
        self.sync_arcmap_context()
        if self._alive:
            self.root.after(2000, self._poll_arcmap_context)

    def sync_arcmap_context(self):
        ctx = gee_bridge.read_arcmap_context()
        if ctx:
            old_time = self.arcmap_context.get('time', 0)
            new_time = ctx.get('time', 0)
            self.arcmap_context = ctx
            self.update_map_scale_display()

            if new_time != old_time:
                # Atualizar lista de camadas raster se houver novidades
                rasters = ctx.get('raster_layers', [])
                if rasters:
                    cur = self.cbo_toc_rasters.get()
                    self.cbo_toc_rasters['values'] = rasters
                    if not cur or cur not in rasters:
                        self.cbo_toc_rasters.current(0)
                # Atualizar camadas vetoriais
                vectors = ctx.get('vector_layers', [])
                if vectors and (not self.cbo_layers['values'] or self.cbo_layers['values'][0] == "Nenhuma camada encontrada"):
                    self.cbo_layers['values'] = vectors
                    self.cbo_layers.current(0)

    def setup_ui(self):
        # 1. Barra de Topo: Status de Conexao, Projeto e Escala Atual
        self.top_frame = tk.Frame(self.root, bg="#fcf3cf", padx=10, pady=6, relief=tk.GROOVE, bd=1)
        self.top_frame.pack(fill=tk.X, side=tk.TOP, padx=6, pady=4)

        # Icone simples e nitido da aplicacao na barra superior (a esquerda de v1.4)
        self.top_icon_img = get_tk_image("icon24") or get_tk_image("icon20") or get_tk_image("icon16")
        if self.top_icon_img:
            self.lbl_top_ico = tk.Label(self.top_frame, image=self.top_icon_img, bg="#fcf3cf", bd=0)
            self.lbl_top_ico.pack(side=tk.LEFT, padx=(0, 6))

        # Badge de Versao bem visivel
        self.lbl_v_badge = tk.Label(
            self.top_frame,
            text=u" v1.4 ",
            font=("Segoe UI", 9, "bold"),
            bg="#1b4f72",
            fg="#ffffff",
            relief=tk.RIDGE,
            bd=1,
            padx=4,
            pady=1
        )
        self.lbl_v_badge.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_status_icon = tk.Label(self.top_frame, text="[*]", font=("Segoe UI", 10, "bold"), bg="#fcf3cf", fg="#7d6608")
        self.lbl_status_icon.pack(side=tk.LEFT, padx=(2, 6))

        self.lbl_status = tk.Label(
            self.top_frame,
            text=u"Verificando conexao com Google Earth Engine...",
            font=("Segoe UI", 9, "bold"),
            bg="#fcf3cf",
            fg="#7d6608"
        )
        self.lbl_status.pack(side=tk.LEFT, padx=2)

        # Indicador de Escala na barra superior
        self.lbl_scale_info = tk.Label(
            self.top_frame,
            text=u"| Escala: Verificando...",
            font=("Segoe UI", 9),
            bg="#fcf3cf",
            fg="#1b4f72"
        )
        self.lbl_scale_info.pack(side=tk.LEFT, padx=10)

        self.btn_about = ttk.Button(self.top_frame, text=u"ℹ Sobre", command=self.on_open_about)
        self.btn_about.pack(side=tk.RIGHT, padx=4)

        self.btn_settings = ttk.Button(self.top_frame, text=u"⚙ Configurações", command=self.on_open_settings)
        self.btn_settings.pack(side=tk.RIGHT, padx=4)

        btn_fit_scale = ttk.Button(self.top_frame, text="Ajustar 1:500.000", command=self.on_fit_scale_clicked)
        btn_fit_scale.pack(side=tk.RIGHT, padx=4)

        self.btn_check_auth = ttk.Button(self.top_frame, text="Verificar Conexao", command=self.async_check_gee)
        self.btn_check_auth.pack(side=tk.RIGHT, padx=4)

        self.btn_auth = ttk.Button(self.top_frame, text="Configurar Projeto GEE", command=self.on_configure_project)
        self.btn_auth.pack(side=tk.RIGHT, padx=4)

        # 2. Painel Central Dividido (PanedWindow)
        middle_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        middle_paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # --- PAINEL ESQUERDO: PARAMETROS ---
        left_frame = ttk.LabelFrame(middle_paned, text=u" 1. Parametros e Bandas ", padding=10)
        middle_paned.add(left_frame, weight=1)

        # Satelite
        ttk.Label(left_frame, text="Satelite / Sensor:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.var_sensor = tk.StringVar(value="S2")
        self.cbo_sensor = ttk.Combobox(left_frame, textvariable=self.var_sensor, state="readonly", width=34)
        self.cbo_sensor['values'] = [item[0] for item in SENSOR_DISPLAY]
        self.cbo_sensor.current(0)
        self.cbo_sensor.bind("<<ComboboxSelected>>", self.on_sensor_changed)
        self.cbo_sensor.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 6))

        # Composicao de Bandas
        ttk.Label(left_frame, text="Composicao / Multibanda:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.var_comp = tk.StringVar()
        self.cbo_comp = ttk.Combobox(left_frame, textvariable=self.var_comp, state="readonly", width=34)
        self.cbo_comp.bind("<<ComboboxSelected>>", self.on_composition_changed)
        self.cbo_comp.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 4))

        # Bandas personalizadas opcionais (> 3 bandas) ou Formula de Indice
        self.lbl_custom_bands = ttk.Label(left_frame, text=u"Bandas Personalizadas (opcional, ex: B4,B3,B2):", font=("Segoe UI", 8))
        self.lbl_custom_bands.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(2, 1))
        self.txt_custom_bands = ttk.Entry(left_frame, width=34)
        self.txt_custom_bands.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=(0, 4))

        # Modo de Carga no ArcMap (Multibanda vs RGB Rapido)
        mode_box = ttk.LabelFrame(left_frame, text=" Modo de Carga no ArcMap ", padding=4)
        mode_box.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=(0, 6))

        self.var_load_mode = tk.StringVar(value="multiband")
        rb_multi = ttk.Radiobutton(
            mode_box,
            text=u"Multibanda Bruta (Permite Trocar Bandas)",
            variable=self.var_load_mode,
            value="multiband"
        )
        rb_multi.pack(anchor=tk.W, pady=1)

        rb_rgb = ttk.Radiobutton(
            mode_box,
            text=u"RGB Rapido (Visualizacao Pronta 3 Bandas)",
            variable=self.var_load_mode,
            value="rgb"
        )
        rb_rgb.pack(anchor=tk.W, pady=1)

        # Tamanho do Pixel / Resolucao (metros)
        ttk.Label(left_frame, text=u"Tamanho do Pixel (m):", font=("Segoe UI", 9, "bold")).grid(row=7, column=0, sticky=tk.W, pady=2)
        self.var_pixel_size = tk.StringVar(value="10")
        self.cbo_pixel_size = ttk.Combobox(
            left_frame,
            textvariable=self.var_pixel_size,
            values=["10", "15", "20", "30", "60", "100"],
            width=15
        )
        self.cbo_pixel_size.grid(row=7, column=1, sticky=tk.E, pady=2)

        # Intervalo de Datas (Padrao brasileiro DD/MM/AAAA)
        ttk.Label(left_frame, text="Data Inicial (DD/MM/AAAA):").grid(row=8, column=0, sticky=tk.W, pady=2)
        self.txt_start_date = ttk.Entry(left_frame, width=15)
        d_end = datetime.date.today()
        d_start = d_end - datetime.timedelta(days=45)
        self.txt_start_date.insert(0, d_start.strftime("%d/%m/%Y"))
        self.txt_start_date.grid(row=8, column=1, sticky=tk.E, pady=2)

        ttk.Label(left_frame, text="Data Final (DD/MM/AAAA):").grid(row=9, column=0, sticky=tk.W, pady=2)
        self.txt_end_date = ttk.Entry(left_frame, width=15)
        self.txt_end_date.insert(0, d_end.strftime("%d/%m/%Y"))
        self.txt_end_date.grid(row=9, column=1, sticky=tk.E, pady=2)

        # Atalhos de data
        frame_date_shortcuts = ttk.Frame(left_frame)
        frame_date_shortcuts.grid(row=10, column=0, columnspan=2, sticky=tk.EW, pady=(3, 8))

        btn_d30 = ttk.Button(frame_date_shortcuts, text="30d", width=8, command=lambda: self.set_quick_dates(30))
        btn_d30.pack(side=tk.LEFT, padx=1)
        btn_d60 = ttk.Button(frame_date_shortcuts, text="60d", width=8, command=lambda: self.set_quick_dates(60))
        btn_d60.pack(side=tk.LEFT, padx=1)
        btn_d90 = ttk.Button(frame_date_shortcuts, text="90d", width=8, command=lambda: self.set_quick_dates(90))
        btn_d90.pack(side=tk.LEFT, padx=1)

        sep_loc = ttk.Separator(left_frame, orient=tk.HORIZONTAL)
        sep_loc.grid(row=11, column=0, columnspan=2, sticky=tk.EW, pady=6)

        # Filtro Espacial (Apenas Extensao da Tela e Camada Vetorial AOI para garantir 100% de qualidade nativa)
        ttk.Label(left_frame, text=u"Filtro de Localizacao (Resolução Nativa 100%):", font=("Segoe UI", 9, "bold")).grid(row=12, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.var_spatial_type = tk.StringVar(value="extent")

        rb_ext = ttk.Radiobutton(left_frame, text=u"Extensao da Tela do ArcMap (<= 1:500k)", variable=self.var_spatial_type, value="extent")
        rb_ext.grid(row=13, column=0, columnspan=2, sticky=tk.W, pady=2)

        rb_lyr = ttk.Radiobutton(left_frame, text="Camada Vetorial (AOI):", variable=self.var_spatial_type, value="layer")
        rb_lyr.grid(row=14, column=0, sticky=tk.W, pady=2)

        self.cbo_layers = ttk.Combobox(left_frame, state="readonly", width=18)
        self.cbo_layers.grid(row=14, column=1, sticky=tk.EW, padx=2)

        # Botao de Busca
        self.btn_search = ttk.Button(left_frame, text="[ Buscar Imagens no GEE ]", style="Primary.TButton", command=self.on_search_clicked)
        self.btn_search.grid(row=15, column=0, columnspan=2, sticky=tk.EW, pady=12)

        # --- PAINEL DIREITO: TABELA MULTISELECAO E MINIATURA ---
        right_frame = ttk.Frame(middle_paned)
        middle_paned.add(right_frame, weight=3)

        # Tabela com Multi-seleção (selectmode extended)
        table_frame = ttk.LabelFrame(right_frame, text=u" 2. Imagens Disponiveis (Selecione uma ou varias com Ctrl / Shift) ", padding=6)
        table_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 4))

        cols = ("date", "cloud", "tile", "name")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("date", text="Data / Hora")
        self.tree.heading("cloud", text="Nuvens (%)")
        self.tree.heading("tile", text="Tile / P-R")
        self.tree.heading("name", text="Nome da Cena")

        self.tree.column("date", width=130, anchor=tk.CENTER)
        self.tree.column("cloud", width=75, anchor=tk.CENTER)
        self.tree.column("tile", width=85, anchor=tk.CENTER)
        self.tree.column("name", width=360, anchor=tk.W)

        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_image_selected)

        # Painel da Miniatura Sob Medida e Acoes de Carregamento
        thumb_frame = ttk.LabelFrame(right_frame, text=u" 3. Pre-Visualizacao & Carregamento em Segundo Plano ", padding=8)
        thumb_frame.pack(fill=tk.BOTH, expand=False, side=tk.BOTTOM)

        thumb_box = ttk.Frame(thumb_frame)
        thumb_box.pack(fill=tk.X)

        self.lbl_thumb = tk.Label(
            thumb_box,
            text=u"Nenhuma miniatura gerada.\nSelecione uma imagem na tabela e clique\nem '[ Gerar Miniatura ]'.",
            width=36,
            height=10,
            bg="#f2f3f4",
            relief=tk.SUNKEN
        )
        self.lbl_thumb.pack(side=tk.LEFT, padx=(0, 12), pady=2)

        info_actions = ttk.Frame(thumb_box)
        info_actions.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.lbl_selected_title = ttk.Label(info_actions, text="Nenhuma imagem selecionada", font=("Segoe UI", 9, "bold"))
        self.lbl_selected_title.pack(anchor=tk.W, pady=1)

        self.lbl_selected_info = ttk.Label(info_actions, text="Selecione cenas na tabela (use Ctrl/Shift para selecionar varias).", font=("Segoe UI", 8), foreground="#566573")
        self.lbl_selected_info.pack(anchor=tk.W, pady=1)

        # Agrupamento no TOC (Group Layer)
        grp_frame = ttk.Frame(info_actions)
        grp_frame.pack(anchor=tk.W, fill=tk.X, pady=(3, 3))

        self.var_use_group = tk.BooleanVar(value=True)
        self.chk_group = ttk.Checkbutton(
            grp_frame,
            text="Agrupar no TOC (Grupo):",
            variable=self.var_use_group,
            command=self.on_toggle_group
        )
        self.chk_group.pack(side=tk.LEFT, padx=(0, 6))

        self.txt_group_name = ttk.Entry(grp_frame, width=28)
        self.txt_group_name.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Mapeamento e Substituicao de Camadas no TOC
        replace_frame = ttk.Frame(info_actions)
        replace_frame.pack(anchor=tk.W, fill=tk.X, pady=(2, 4))

        ttk.Label(replace_frame, text="Mapear/Substituir no TOC:", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.cbo_toc_rasters = ttk.Combobox(replace_frame, state="readonly", width=22)
        self.cbo_toc_rasters.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        btn_refresh_toc = ttk.Button(replace_frame, text="Atualizar", width=9, command=self.refresh_toc_rasters)
        btn_refresh_toc.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_replace_toc = ttk.Button(
            replace_frame,
            text="[ Substituir no TOC ]",
            command=self.on_replace_selected_background
        )
        self.btn_replace_toc.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_apply_comp_toc = ttk.Button(
            replace_frame,
            text=u"[ Aplicar Composição ]",
            command=self.on_apply_comp_to_toc_layer
        )
        self.btn_apply_comp_toc.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_apply_stretch = ttk.Button(
            replace_frame,
            text=u"⚡ [ Garantir Stretch ]",
            command=self.on_apply_stretch_to_toc
        )
        self.btn_apply_stretch.pack(side=tk.LEFT)

        # Botoes de Acao
        btn_bar = ttk.Frame(info_actions)
        btn_bar.pack(anchor=tk.W, pady=4)

        self.btn_gen_thumb = ttk.Button(btn_bar, text="[ Gerar Miniatura ]", command=self.on_refresh_thumb_clicked)
        self.btn_gen_thumb.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_open_browser = ttk.Button(btn_bar, text="[ Abrir no Navegador ]", command=self.on_open_browser_clicked)
        self.btn_open_browser.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_add_toc = ttk.Button(
            btn_bar,
            text="[ Carregar no ArcMap ]",
            style="Action.TButton",
            command=self.on_load_selected_background
        )
        self.btn_add_toc.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_mosaic_toc = ttk.Button(
            btn_bar,
            text="[ Criar Mosaico ]",
            command=self.on_load_mosaic_background
        )
        self.btn_mosaic_toc.pack(side=tk.LEFT)

        # 3. Barra de Status Inferior com Progresso
        self.lbl_progress = ttk.Label(self.root, text=u"Pronto. (CGMA ArcGEE Explorer v1.4 - Resolução Nativa Estrita 100%)", relief=tk.SUNKEN, anchor=tk.W, padding=4)
        self.lbl_progress.pack(fill=tk.X, side=tk.BOTTOM)

    def update_map_scale_display(self):
        scale = self.arcmap_context.get('scale')
        if scale is not None:
            if scale <= MAX_ALLOWED_SCALE:
                self.lbl_scale_info.config(
                    text=u"| Escala ArcMap: 1:{:,.0f} (Valida <= 1:500k [OK])".format(scale),
                    fg="#145a32"
                )
            else:
                self.lbl_scale_info.config(
                    text=u"| Escala ArcMap: 1:{:,.0f} (Excede 1:500k [Alerta])".format(scale),
                    fg="#922b21"
                )
        else:
            self.lbl_scale_info.config(text=u"| Escala: N/D", fg="#555")

    def on_fit_scale_clicked(self):
        self.lbl_progress.config(text="Ajustando escala no ArcMap para 1:500.000...")
        rep = gee_bridge.send_arcmap_command({'action': 'set_scale', 'scale': MAX_ALLOWED_SCALE})
        if rep.get('success'):
            self.sync_arcmap_context()
            messagebox.showinfo("Escala Ajustada", "A escala do mapa foi ajustada para 1:500.000 no ArcMap!", parent=self.root)
            self.lbl_progress.config(text="Escala ajustada para 1:500.000.")
        else:
            messagebox.showwarning("Aviso", "Nao foi possivel ajustar a escala: " + rep.get('message', ''), parent=self.root)

    def set_quick_dates(self, days):
        d_end = datetime.date.today()
        d_start = d_end - datetime.timedelta(days=days)
        self.txt_start_date.delete(0, tk.END)
        self.txt_start_date.insert(0, d_start.strftime("%d/%m/%Y"))
        self.txt_end_date.delete(0, tk.END)
        self.txt_end_date.insert(0, d_end.strftime("%d/%m/%Y"))

    def populate_initial_data(self):
        ctx = gee_bridge.read_arcmap_context() or {}
        self.arcmap_context = ctx
        layers = ctx.get('vector_layers', [])
        if layers:
            self.cbo_layers['values'] = layers
            self.cbo_layers.current(0)
        else:
            self.cbo_layers['values'] = ["Nenhuma camada encontrada"]
            self.cbo_layers.current(0)

        self.update_compositions_list()
        self.update_default_group_name()
        self.refresh_toc_rasters()

    def refresh_toc_rasters(self):
        try:
            self.sync_arcmap_context()
            rasters = self.arcmap_context.get('raster_layers', [])
            if rasters:
                cur = self.cbo_toc_rasters.get()
                self.cbo_toc_rasters['values'] = rasters
                if not cur or cur not in rasters:
                    self.cbo_toc_rasters.current(0)
            else:
                self.cbo_toc_rasters['values'] = ["Nenhuma camada raster no TOC"]
                self.cbo_toc_rasters.current(0)
        except Exception as e:
            print("Erro ao atualizar camadas raster do TOC:", e)

    def update_default_group_name(self):
        try:
            sensor = self.get_selected_sensor_code()
            comp = self.get_selected_composition_code()
            today_str = datetime.date.today().strftime("%Y%m%d")
            default_name = "GEE_%s_%s_%s" % (sensor, comp, today_str)
            if hasattr(self, 'txt_group_name'):
                current = self.txt_group_name.get().strip()
                if not current or current.startswith("GEE_"):
                    self.txt_group_name.delete(0, tk.END)
                    self.txt_group_name.insert(0, default_name)
        except Exception:
            pass

    def on_toggle_group(self):
        if self.var_use_group.get():
            self.txt_group_name.config(state=tk.NORMAL)
        else:
            self.txt_group_name.config(state=tk.DISABLED)

    def get_selected_sensor_code(self):
        idx = self.cbo_sensor.current()
        if 0 <= idx < len(SENSOR_DISPLAY):
            return SENSOR_DISPLAY[idx][1]
        return "S2"

    def on_sensor_changed(self, event=None):
        self.update_compositions_list()
        self.update_default_group_name()
        # Atualizar tamanho do pixel padrao de acordo com a resolucao nativa do satelite
        if hasattr(self, 'var_pixel_size'):
            s = self.get_selected_sensor_code()
            if s == "S2":
                self.var_pixel_size.set("10")
            elif s in ["L8", "L7", "L5", "L4"]:
                self.var_pixel_size.set("30")
            elif s in ["L1", "L2", "L3"]:
                self.var_pixel_size.set("60")

    def update_compositions_list(self):
        sensor = self.get_selected_sensor_code()
        resp = gee_bridge.get_compositions(sensor)
        if resp.get('success'):
            comps = resp.get('compositions', {})
            items = []
            for code, data in sorted(comps.items()):
                label = data.get('label', '')
                items.append("%s - %s" % (code, label))
            self.cbo_comp['values'] = items
            if items:
                self.cbo_comp.current(0)
        else:
            self.cbo_comp['values'] = []

    def on_composition_changed(self, event=None):
        self.update_default_group_name()
        comp = self.get_selected_composition_code()
        sensor = self.get_selected_sensor_code()

        if hasattr(self, 'lbl_custom_bands'):
            if comp == 'CUSTOM_MATH':
                self.lbl_custom_bands.config(text=u"Fórmula Matemática (ex: (B8-B4)/(B8+B4) ou (SR_B5-SR_B4)/(SR_B5+SR_B4)):")
                curr = self.txt_custom_bands.get().strip()
                if not curr or curr in ['B4,B3,B2', 'SR_B4,SR_B3,SR_B2']:
                    def_formula = "(B8-B4)/(B8+B4)" if sensor == "S2" else "(SR_B5-SR_B4)/(SR_B5+SR_B4)"
                    self.txt_custom_bands.delete(0, tk.END)
                    self.txt_custom_bands.insert(0, def_formula)
            elif comp in ['NDVI', 'NDWI', 'NDMI', 'NBR', 'EVI', 'SAVI']:
                self.lbl_custom_bands.config(text=u"Índice Espectral (cálculo e paleta automáticos no GEE):")
            else:
                self.lbl_custom_bands.config(text=u"Bandas Personalizadas (opcional, separadas por vírgula):")

        # Nao carregar miniatura automaticamente; apenas sob demanda via clique no botao
        if self.get_selected_image_id():
            self.lbl_thumb.config(
                text=u"Composição alterada.\nClique em '[ Gerar Miniatura ]'\npara visualizar.",
                image=""
            )
            self.thumb_photo = None
            self.current_thumb_url = None

    def async_check_gee(self):
        def do_check():
            resp = gee_bridge.check_gee()
            def apply_status():
                try:
                    if not self._alive:
                        return
                    if resp.get('success'):
                        self.is_authenticated = True
                        self.top_frame.config(bg="#d4efdf")
                        if hasattr(self, 'lbl_top_ico') and self.lbl_top_ico is not None:
                            self.lbl_top_ico.config(bg="#d4efdf")
                        self.lbl_status_icon.config(text="[OK]", bg="#d4efdf", fg="#145a32")
                        self.lbl_status.config(text=resp.get('message', 'Conectado ao Google Earth Engine!'), bg="#d4efdf", fg="#145a32")
                        self.btn_auth.config(text="Configurar Projeto GEE")
                    else:
                        self.is_authenticated = False
                        self.top_frame.config(bg="#fadbd8")
                        if hasattr(self, 'lbl_top_ico') and self.lbl_top_ico is not None:
                            self.lbl_top_ico.config(bg="#fadbd8")
                        self.lbl_status_icon.config(text="[X]", bg="#fadbd8", fg="#922b21")
                        self.lbl_status.config(text=resp.get('message', 'Nao conectado ao GEE'), bg="#fadbd8", fg="#922b21")
                        self.btn_auth.config(text="Autenticar GEE")
                except Exception as ex:
                    print("Erro ao atualizar status:", ex)

            self.post_to_gui(apply_status)

        threading.Thread(target=do_check).start()

    def on_configure_project(self):
        proj = simpledialog.askstring(
            "Configurar Projeto Google Cloud / GEE",
            "Informe o ID do Projeto Google Cloud habilitado no Earth Engine:\n(Exemplo: meu-projeto-gee-123)",
            parent=self.root
        )
        if proj is not None and proj.strip():
            proj = proj.strip()
            self.lbl_status.config(text="Configurando projeto '%s'..." % proj)
            def do_auth():
                resp = gee_bridge.authenticate_gee(project=proj)
                def apply_auth():
                    if resp.get('success'):
                        messagebox.showinfo("Sucesso", resp.get('message'), parent=self.root)
                        self.async_check_gee()
                    else:
                        if "Nao autenticado" in resp.get('message', ''):
                            if messagebox.askyesno(
                                "Autenticacao Necessaria",
                                "Sua conta ainda nao esta logada neste computador.\n\nDeseja abrir a janela de autenticacao agora?",
                                parent=self.root
                            ):
                                gee_bridge.launch_auth_console(project=proj)
                        else:
                            messagebox.showerror("Erro de Conexao", resp.get('message'), parent=self.root)
                        self.async_check_gee()
                self.post_to_gui(apply_auth)

            threading.Thread(target=do_auth).start()
        elif proj is not None and not proj.strip():
            gee_bridge.launch_auth_console()

    def on_open_settings(self):
        """Abre a janela modal de configuracoes de Stretch, Estatisticas, Multicore e AOI Buffer"""
        GEESettingsDialog(self)

    def on_open_about(self):
        """Abre a janela modal Sobre com informacoes institucionais e dicas"""
        GEEAboutDialog(self.root)

    def on_open_updater(self):
        """Abre a janela modal de atualizacao do plugin via GitHub ou ZIP local"""
        GEEUpdaterDialog(self)

    def get_selected_composition_code(self):
        val = self.var_comp.get()
        if val and " - " in val:
            return val.split(" - ")[0].strip()
        return "432"

    def get_selected_image_id(self):
        selected = self.tree.selection()
        if not selected:
            return None
        idx = self.tree.index(selected[0])
        if 0 <= idx < len(self.images_cache):
            return self.images_cache[idx].get('id')
        return None

    def get_all_selected_image_ids(self):
        selected = self.tree.selection()
        ids = []
        for s in selected:
            idx = self.tree.index(s)
            if 0 <= idx < len(self.images_cache):
                ids.append(self.images_cache[idx].get('id'))
        return ids

    def on_search_clicked(self):
        if not self.is_authenticated:
            if messagebox.askyesno(
                "Autenticacao Necessaria",
                "O Google Earth Engine ainda nao esta conectado.\n\nDeseja abrir a tela de autenticacao agora no navegador?",
                parent=self.root
            ):
                self.on_configure_project()
            return

        self.sync_arcmap_context()

        st = self.var_spatial_type.get()
        bbox = None
        geojson_file = None

        if st == "extent":
            bbox = self.arcmap_context.get('bbox')
            if not bbox:
                bbox = [-61.64, -18.04, -50.22, -7.35]

        sensor = self.get_selected_sensor_code()
        s_date = normalize_date(self.txt_start_date.get())
        e_date = normalize_date(self.txt_end_date.get())

        self.btn_search.config(state=tk.DISABLED)
        self.lbl_progress.config(text="Iniciando busca no Google Earth Engine...")

        def run_search_thread():
            try:
                g_file = None
                if st == "layer":
                    lyr_name = self.cbo_layers.get()
                    if lyr_name and lyr_name != "Nenhuma camada encontrada":
                        buf = float(self.settings.get('aoi_buffer_meters', 0.0) if hasattr(self, 'settings') else 0.0)
                        self.post_to_gui(lambda: self.lbl_progress.config(text="Exportando AOI da camada '%s' do ArcMap..." % lyr_name))
                        rep = gee_bridge.send_arcmap_command({'action': 'export_aoi', 'layer_name': lyr_name, 'buffer_meters': buf}, timeout=15)
                        if rep.get('success'):
                            g_file = rep.get('file')

                self.post_to_gui(lambda: self.lbl_progress.config(text="Buscando imagens no catalogo do Google Earth Engine... Aguarde."))
                resp = gee_bridge.search_images(
                    sensor=sensor,
                    start_date=s_date,
                    end_date=e_date,
                    bbox=bbox,
                    geojson_file=g_file,
                    max_images=100
                )

                def update_tree():
                    for row_id in self.tree.get_children():
                        self.tree.delete(row_id)
                    self.images_cache = []

                    if not resp.get('success'):
                        err_msg = resp.get('message', 'Erro desconhecido')
                        messagebox.showerror("Erro de Busca", err_msg, parent=self.root)
                        self.lbl_progress.config(text="Falha na busca: " + err_msg[:60])
                        return

                    images = resp.get('images', [])
                    self.images_cache = images

                    for img in images:
                        tile_str = img.get('mgrs') or ("%s/%s" % (img.get('path', ''), img.get('row', '')) if img.get('path') else '')
                        self.tree.insert("", tk.END, values=(
                            img.get('date'),
                            "%s%%" % img.get('cloud_pct'),
                            tile_str,
                            img.get('name') or img.get('id', '').split('/')[-1]
                        ))

                    count = len(images)
                    self.lbl_progress.config(text="Busca concluida: %d imagens encontradas." % count)
                    if count > 0:
                        first_item = self.tree.get_children()[0]
                        self.tree.selection_set(first_item)
                        self.on_image_selected()
                    else:
                        messagebox.showinfo("Nenhum Resultado", "Nenhuma imagem foi encontrada para os filtros e periodo especificados.", parent=self.root)

                self.post_to_gui(update_tree)
            except Exception as e:
                err_text = str(e)
                def show_err():
                    messagebox.showerror("Erro Inesperado", err_text, parent=self.root)
                    self.lbl_progress.config(text="Erro: " + err_text[:60])
                self.post_to_gui(show_err)
            finally:
                def reenable():
                    try:
                        self.btn_search.config(state=tk.NORMAL)
                    except Exception:
                        pass
                self.post_to_gui(reenable)

        threading.Thread(target=run_search_thread).start()

    def on_image_selected(self, event=None):
        selected_ids = self.get_all_selected_image_ids()
        count = len(selected_ids)
        if count == 0:
            self.lbl_selected_title.config(text="Nenhuma imagem selecionada")
            self.lbl_selected_info.config(text="Selecione uma ou mais imagens na tabela.")
            return

        if count == 1:
            full_id = selected_ids[0]
            short_name = full_id.split('/')[-1]
            self.lbl_selected_title.config(text=short_name)

            for img in self.images_cache:
                if img.get('id') == full_id:
                    self.lbl_selected_info.config(
                        text="Data: %s | Nuvens: %s%% | Tile: %s" % (
                            img.get('date'),
                            img.get('cloud_pct'),
                            img.get('mgrs') or ("%s/%s" % (img.get('path', ''), img.get('row', '')))
                        )
                    )
                    break
            # Nao carregar miniatura automaticamente; apenas se clicado no botao [ Gerar Miniatura ]
            self.lbl_thumb.config(
                text=u"Cena selecionada.\nClique em '[ Gerar Miniatura ]'\npara carregar pré-visualização.",
                image=""
            )
            self.thumb_photo = None
            self.current_thumb_url = None
        else:
            self.lbl_selected_title.config(text="%d imagens selecionadas" % count)
            self.lbl_selected_info.config(
                text=u"Multi-seleção ativa. Você pode carregar todas juntas ou criar um mosaico único."
            )
            self.lbl_thumb.config(
                text=u"Multi-seleção (%d cenas).\nSelecione 1 imagem para miniatura." % count,
                image=""
            )
            self.thumb_photo = None
            self.current_thumb_url = None

    def on_refresh_thumb_clicked(self):
        full_id = self.get_selected_image_id()
        if not full_id:
            messagebox.showinfo(u"Aviso", u"Selecione uma imagem na tabela para gerar a miniatura.", parent=self.root)
            return

        sensor = self.get_selected_sensor_code()
        comp = self.get_selected_composition_code()

        self.lbl_thumb.config(text=u"Carregando miniatura sob medida...\nAguarde alguns segundos.", image="")
        self.btn_gen_thumb.config(state=tk.DISABLED)
        self.lbl_progress.config(text=u"Gerando miniatura sob medida no Google Earth Engine...")

        def run_thumb():
            tmp_png = os.path.join(tempfile.gettempdir(), "gee_thumb.png")
            resp = gee_bridge.get_thumbnail(full_id, sensor, comp, tmp_png)

            def show_thumb():
                self.btn_gen_thumb.config(state=tk.NORMAL)
                if resp.get('success'):
                    self.current_thumb_url = resp.get('url')
                    gif_file = resp.get('gif') or resp.get('file')
                    if gif_file and os.path.exists(gif_file):
                        try:
                            self.thumb_photo = tk.PhotoImage(file=gif_file)
                            self.lbl_thumb.config(image=self.thumb_photo, text="")
                            self.lbl_progress.config(text="Miniatura gerada com sucesso!")
                            return
                        except Exception as e:
                            print("Erro exibindo foto:", e)
                    self.lbl_thumb.config(text="Miniatura gerada com sucesso!\nClique ao lado para abrir no navegador.", image="")
                    self.lbl_progress.config(text="Miniatura disponivel.")
                else:
                    err_msg = resp.get('message', 'Erro')
                    self.lbl_thumb.config(text="Falha ao gerar miniatura:\n" + err_msg[:50], image="")
                    self.lbl_progress.config(text="Erro na miniatura: " + err_msg[:60])

            self.post_to_gui(show_thumb)

        threading.Thread(target=run_thumb).start()

    def on_open_browser_clicked(self):
        if self.current_thumb_url:
            webbrowser.open(self.current_thumb_url)
        else:
            messagebox.showinfo("Aviso", "Nenhuma miniatura ativa no momento. Selecione uma imagem primeiro.", parent=self.root)

    def validate_scale_and_get_bbox(self):
        """Valida se a escala do ArcMap esta dentro de 1:500.000 para busca por extensao.
        Retorna (ok, bbox, auto_zoom):
        - Para Camada (AOI): exporta geojson, bbox=None e auto_zoom=True.
        - Para Extensao da Tela: valida escala <= 1:500k, bbox da tela e auto_zoom=False.
        """
        st = self.var_spatial_type.get()

        if st == "layer":
            lyr_name = self.cbo_layers.get()
            if not lyr_name or lyr_name == "Nenhuma camada encontrada":
                messagebox.showwarning(u"Camada Inválida", u"Selecione uma camada vetorial (AOI) válida no ArcMap.", parent=self.root)
                return False, None, False
            buf = float(self.settings.get('aoi_buffer_meters', 0.0) if hasattr(self, 'settings') else 0.0)
            rep = gee_bridge.send_arcmap_command({'action': 'export_aoi', 'layer_name': lyr_name, 'buffer_meters': buf}, timeout=10)
            if rep.get('success'):
                self.current_aoi_file = rep.get('file')
            else:
                messagebox.showerror(u"Erro AOI", u"Falha ao exportar limite vetorial da camada '%s': %s" % (lyr_name, rep.get('message', '')), parent=self.root)
                return False, None, False
            return True, None, True

        # st == "extent"
        self.sync_arcmap_context()
        scale = self.arcmap_context.get('scale')

        if scale is not None and scale > MAX_ALLOWED_SCALE:
            msg = (
                "A escala atual do mapa e 1:{:,.0f}, superior a escala maxima permitida de 1:500.000.\n\n"
                "Deseja ajustar o zoom do ArcMap automaticamente para 1:500.000 para continuar?"
            ).format(scale)
            if messagebox.askyesno("Limite de Escala (1:500.000)", msg, parent=self.root):
                gee_bridge.send_arcmap_command({'action': 'set_scale', 'scale': MAX_ALLOWED_SCALE})
                self.sync_arcmap_context()
            else:
                return False, None, False

        bbox = self.arcmap_context.get('bbox')
        if not bbox:
            rep = gee_bridge.send_arcmap_command({'action': 'refresh_context'}, timeout=5)
            if rep.get('success') and rep.get('context'):
                self.arcmap_context = rep['context']
                bbox = self.arcmap_context.get('bbox')
        if not bbox:
            bbox = [-61.64, -18.04, -50.22, -7.35]

        return True, bbox, False

    def on_load_selected_background(self):
        """Carrega todas as imagens selecionadas no ArcMap em segundo plano"""
        ids = self.get_all_selected_image_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione pelo menos uma imagem na tabela.", parent=self.root)
            return

        ok, bbox, auto_zoom = self.validate_scale_and_get_bbox()
        if not ok:
            return

        self._start_background_download(ids, is_mosaic=False, bbox=bbox, auto_zoom=auto_zoom)

    def on_load_mosaic_background(self):
        """Cria e carrega mosaico das imagens selecionadas em segundo plano"""
        ids = self.get_all_selected_image_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione pelo menos uma imagem na tabela para o mosaico.", parent=self.root)
            return

        ok, bbox, auto_zoom = self.validate_scale_and_get_bbox()
        if not ok:
            return

        self._start_background_download(ids, is_mosaic=True, bbox=bbox, auto_zoom=auto_zoom)

    def on_replace_selected_background(self):
        """Substitui uma camada selecionada no TOC pela imagem atual do GEE"""
        ids = self.get_all_selected_image_ids()
        if not ids:
            messagebox.showwarning("Aviso", "Selecione uma imagem na tabela para substituir.", parent=self.root)
            return

        target_layer = self.cbo_toc_rasters.get()
        if not target_layer or target_layer == "Nenhuma camada raster no TOC":
            messagebox.showwarning("Aviso", "Selecione qual camada do TOC voce deseja substituir na lista ao lado.", parent=self.root)
            return

        ok, bbox, auto_zoom = self.validate_scale_and_get_bbox()
        if not ok:
            return

        self._start_background_download(ids[:1], is_mosaic=False, bbox=bbox, replace_target=target_layer, auto_zoom=auto_zoom)

    def on_apply_comp_to_toc_layer(self):
        """Aplica a composicao de bandas selecionada na combobox diretamente na camada selecionada no TOC"""
        target_layer = self.cbo_toc_rasters.get()
        if not target_layer or target_layer == "Nenhuma camada raster no TOC":
            messagebox.showwarning("Aviso", "Selecione qual camada do TOC voce deseja alterar na lista ao lado.", parent=self.root)
            return

        sensor = self.get_selected_sensor_code()
        comp = self.get_selected_composition_code()

        self.lbl_progress.config(text="Alterando composicao da camada '%s' para %s no ArcMap..." % (target_layer, comp))
        self.btn_apply_comp_toc.config(state=tk.DISABLED)

        def worker():
            try:
                rep = gee_bridge.send_arcmap_command({
                    'action': 'change_composition',
                    'target_layer': target_layer,
                    'comp': comp,
                    'sensor': sensor
                }, timeout=30)

                def finish():
                    if rep.get('success'):
                        self.lbl_progress.config(text="Composicao alterada com sucesso!")
                        messagebox.showinfo("Sucesso", rep.get('message', 'Composicao alterada no ArcMap!'), parent=self.root)
                    else:
                        err_m = rep.get('message', 'Falha ao alterar composicao')
                        self.lbl_progress.config(text="Falha: " + err_m[:50])
                        messagebox.showwarning("Aviso ArcMap", "ArcMap retornou: " + err_m, parent=self.root)

                self.post_to_gui(finish)
            except Exception as ex:
                def on_err():
                    messagebox.showerror("Erro", str(ex), parent=self.root)
                self.post_to_gui(on_err)
            finally:
                self.post_to_gui(lambda: self.btn_apply_comp_toc.config(state=tk.NORMAL))

        threading.Thread(target=worker).start()

    def on_apply_stretch_to_toc(self):
        """Garante e aplica as configurações ativas de Stretch e DRA nas camadas raster do ArcMap"""
        target_layer = self.cbo_toc_rasters.get().strip() if hasattr(self, 'cbo_toc_rasters') else ""
        if not target_layer or target_layer in ("Nenhuma camada raster no TOC", "Nenhuma camada encontrada"):
            target_layer = None

        desc = (u"na camada '%s'" % target_layer) if target_layer else u"em todas as camadas raster do TOC"
        self.lbl_progress.config(text=u"Aplicando e garantindo configurações de stretch %s..." % desc)
        if hasattr(self, 'btn_apply_stretch'):
            self.btn_apply_stretch.config(state=tk.DISABLED)

        def worker():
            try:
                rep = gee_bridge.apply_stretch(target_layer, settings=self.settings)
                def finish():
                    if rep.get('success'):
                        msg = rep.get('message', u'Configurações de stretch garantidas com sucesso!')
                        self.lbl_progress.config(text=msg)
                        messagebox.showinfo(u"Stretch Garantido", msg, parent=self.root)
                    else:
                        err_m = rep.get('message', u'Falha ao aplicar stretch.')
                        self.lbl_progress.config(text=u"Aviso: " + err_m[:50])
                        messagebox.showwarning(u"Aviso ArcMap", err_m, parent=self.root)
                self.post_to_gui(finish)
            except Exception as ex:
                def on_err():
                    messagebox.showerror(u"Erro", str(ex), parent=self.root)
                self.post_to_gui(on_err)
            finally:
                def reenable():
                    if hasattr(self, 'btn_apply_stretch'):
                        self.btn_apply_stretch.config(state=tk.NORMAL)
                self.post_to_gui(reenable)

        threading.Thread(target=worker).start()

    def _start_background_download(self, image_ids, is_mosaic, bbox, replace_target=None, auto_zoom=False):
        if self.is_downloading:
            messagebox.showwarning("Em Andamento", "Ja existe um carregamento em segundo plano em execucao.", parent=self.root)
            return

        sensor = self.get_selected_sensor_code()
        comp = self.get_selected_composition_code()
        custom_bands = self.txt_custom_bands.get().strip() or None
        load_mode = self.var_load_mode.get() if hasattr(self, 'var_load_mode') else 'multiband'
        st = self.var_spatial_type.get()
        geojson_file = getattr(self, 'current_aoi_file', None) if (st == "layer") else None

        # Obter tamanho do pixel / resolucao definida pelo usuario
        pixel_size = None
        if hasattr(self, 'var_pixel_size'):
            raw_px = self.var_pixel_size.get().strip()
            if raw_px:
                try:
                    pixel_size = float(raw_px)
                except Exception:
                    pixel_size = None

        # Validacao preventiva de tamanho para resolucao nativa estrita (100% de qualidade)
        if st == "extent" and bbox:
            import math
            req_scale = pixel_size
            if req_scale is None or req_scale <= 0:
                if sensor == "S2":
                    req_scale = 10.0
                elif sensor in ["L8", "L7", "L5", "L4"]:
                    req_scale = 30.0
                elif sensor in ["L1", "L2", "L3"]:
                    req_scale = 60.0
                else:
                    req_scale = 30.0

            # Determinar numero de bandas estimado
            comp_is_index = comp in ['NDVI', 'NDWI', 'NDMI', 'NBR', 'EVI', 'SAVI', 'CUSTOM_MATH']
            if comp_is_index:
                n_b = 1
                bpp = 4  # Float32
            elif load_mode == 'multiband':
                if custom_bands:
                    n_b = len([b for b in custom_bands.split(',') if b.strip()])
                elif comp == 'MB_10':
                    n_b = 10
                elif comp == 'MB_12':
                    n_b = 12
                elif comp == 'MB_6':
                    n_b = 6
                else:
                    n_b = 3
                bpp = 2 * n_b  # Int16 por banda
            else:
                n_b = 3
                bpp = 3  # RGB 8-bit

            minx, miny, maxx, maxy = bbox
            lat_center = (miny + maxy) / 2.0
            lat_rad = math.radians(lat_center)
            width_m = abs(maxx - minx) * 111320.0 * math.cos(lat_rad)
            height_m = abs(maxy - miny) * 110540.0
            area_m2 = max(width_m * height_m, 1000.0)
            est_bytes = (area_m2 / (req_scale * req_scale)) * bpp
            target_max_bytes = 48 * 1024 * 1024

            if est_bytes > target_max_bytes * 1.05:
                est_mb = round(est_bytes / (1024.0 * 1024.0), 1)
                area_km2 = round(area_m2 / 1000000.0, 1)
                messagebox.showerror(
                    u"Qualidade Nativa Estrita (Limite Excedido)",
                    u"A extensão atual da tela (%.0f km²) requer aproximadamente %.1f MB para a resolução nativa de %.0fm com %d banda(s), excedendo o limite de 48 MB do Google Earth Engine.\n\n"
                    u"Para garantir 100%% da nitidez e qualidade original sem qualquer perda por reamostragem, o download foi impedido.\n\n"
                    u"Solução: Aumente o zoom no ArcMap (escala <= 1:250.000 para Sentinel-2 ou selecione menos bandas) ou utilize uma camada vetorial (AOI) menor." % (
                        area_km2, est_mb, req_scale, n_b
                    ),
                    parent=self.root
                )
                return

        # Obter informacao do Grupo na thread principal
        group_name = None
        if not replace_target and self.var_use_group.get():
            g_val = self.txt_group_name.get().strip()
            if g_val:
                group_name = g_val

        self.is_downloading = True
        self.btn_add_toc.config(state=tk.DISABLED)
        self.btn_mosaic_toc.config(state=tk.DISABLED)
        if hasattr(self, 'btn_replace_toc'):
            self.btn_replace_toc.config(state=tk.DISABLED)
        if hasattr(self, 'btn_apply_comp_toc'):
            self.btn_apply_comp_toc.config(state=tk.DISABLED)

        total = len(image_ids)
        if replace_target:
            self.lbl_progress.config(text="[Segundo Plano] Baixando imagem para substituir '%s' no TOC..." % replace_target)
        else:
            self.lbl_progress.config(text="[Segundo Plano] Iniciando download de %d imagem(ns)..." % total)

        def worker():
            loaded_count = 0
            try:
                if replace_target:
                    # Substituicao de camada existente no TOC
                    img_id = image_ids[0]
                    short_name = img_id.split('/')[-1]
                    layer_title = "%s_%s" % (short_name, comp)
                    out_tif = os.path.join(tempfile.gettempdir(), "%s.tif" % layer_title)

                    resp = gee_bridge.download_image(
                        image_ids=[img_id],
                        sensor=sensor,
                        comp_code=comp,
                        out_tif=out_tif,
                        custom_bands=custom_bands,
                        load_mode=load_mode,
                        bbox=bbox,
                        geojson_file=geojson_file,
                        scale=pixel_size
                    )

                    if resp.get('success'):
                        tif_file = resp.get('file')
                        self.post_to_gui(lambda: self.lbl_progress.config(text="Enviando comando para substituir camada no ArcMap..."))
                        rep = gee_bridge.send_arcmap_command({
                            'action': 'replace_layer',
                            'file': tif_file,
                            'target_layer': replace_target,
                            'name': layer_title,
                            'comp': comp,
                            'sensor': sensor,
                            'custom_bands': custom_bands
                        }, timeout=120)
                        if rep.get('success'):
                            loaded_count = 1
                        else:
                            err_msg = rep.get('message', '')
                            self.post_to_gui(lambda m=err_msg: messagebox.showwarning("Aviso ArcMap", "ArcMap retornou: " + m, parent=self.root))
                    else:
                        err = resp.get('message', 'Erro desconhecido ao baixar imagem.')
                        self.post_to_gui(lambda m=err: messagebox.showerror("Erro ao Baixar", m, parent=self.root))
                elif is_mosaic:
                    # Mosaico unico com todas as imagens selecionadas
                    first_name = image_ids[0].split('/')[-1]
                    layer_title = "Mosaico_%s_%s_%s" % (sensor, comp, datetime.date.today().strftime("%Y%m%d"))
                    out_tif = os.path.join(tempfile.gettempdir(), "%s.tif" % layer_title)

                    self.post_to_gui(lambda: self.lbl_progress.config(
                        text="[Segundo Plano] Gerando mosaico de %d imagens no GEE..." % total
                    ))

                    resp = gee_bridge.download_image(
                        image_ids=image_ids,
                        sensor=sensor,
                        comp_code=comp,
                        out_tif=out_tif,
                        custom_bands=custom_bands,
                        load_mode=load_mode,
                        bbox=bbox,
                        geojson_file=geojson_file,
                        scale=pixel_size
                    )

                    if resp.get('success'):
                        tif_file = resp.get('file')
                        self.post_to_gui(lambda: self.lbl_progress.config(text="Enviando mosaico para o TOC do ArcMap..."))
                        rep = gee_bridge.send_arcmap_command({
                            'action': 'load_layer',
                            'file': tif_file,
                            'name': layer_title,
                            'group': group_name,
                            'zoom': auto_zoom,
                            'comp': comp,
                            'sensor': sensor,
                            'custom_bands': custom_bands
                        }, timeout=120)
                        if rep.get('success'):
                            loaded_count = total
                        else:
                            err_msg = rep.get('message', '')
                            self.post_to_gui(lambda m=err_msg: messagebox.showwarning("Aviso ArcMap", "ArcMap retornou: " + m, parent=self.root))
                    else:
                        err = resp.get('message', 'Erro desconhecido ao gerar mosaico.')
                        self.post_to_gui(lambda m=err: messagebox.showerror("Erro Mosaico", m, parent=self.root))
                else:
                    # Carregar cada imagem selecionada individualmente
                    # Verificar se aceleracao multicore esta ativada nas configuracoes
                    settings = gee_bridge.load_plugin_settings()
                    multicore_on = settings.get('multicore_enabled', True)
                    core_count = int(settings.get('multicore_cores', 4))

                    if multicore_on and core_count > 1 and total > 1 and concurrent:
                        num_workers = min(core_count, total)
                        prog_msg = u"[Multicore] Baixando %d imagens em paralelo (%d threads)..." % (total, num_workers)
                        self.post_to_gui(lambda m=prog_msg: self.lbl_progress.config(text=m))

                        ipc_lock = threading.Lock()

                        def process_single_image(idx, img_id):
                            short_name = img_id.split('/')[-1]
                            layer_title = "%s_%s" % (short_name, comp)
                            out_tif = os.path.join(tempfile.gettempdir(), "%s.tif" % layer_title)

                            resp = gee_bridge.download_image(
                                image_ids=[img_id],
                                sensor=sensor,
                                comp_code=comp,
                                out_tif=out_tif,
                                custom_bands=custom_bands,
                                load_mode=load_mode,
                                bbox=bbox,
                                geojson_file=geojson_file,
                                scale=pixel_size
                            )

                            if resp.get('success'):
                                tif_file = resp.get('file')
                                with ipc_lock:
                                    self.post_to_gui(lambda s=short_name: self.lbl_progress.config(
                                        text=u"[Multicore] Carregando %s no TOC..." % s
                                    ))
                                    rep = gee_bridge.send_arcmap_command({
                                        'action': 'load_layer',
                                        'file': tif_file,
                                        'name': layer_title,
                                        'group': group_name,
                                        'zoom': auto_zoom if (idx == 0) else False,
                                        'comp': comp,
                                        'sensor': sensor,
                                        'custom_bands': custom_bands
                                    }, timeout=120)
                                    if rep.get('success'):
                                        return True, short_name, None
                                    else:
                                        return False, short_name, rep.get('message', '')
                            else:
                                return False, short_name, resp.get('message', 'Erro ao baixar imagem.')

                        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                            future_map = {
                                executor.submit(process_single_image, idx, img_id): img_id 
                                for idx, img_id in enumerate(image_ids)
                            }
                            for future in concurrent.futures.as_completed(future_map):
                                ok, short_name, err_msg = future.result()
                                if ok:
                                    loaded_count += 1
                                    self.post_to_gui(lambda c=loaded_count, t=total, s=short_name: self.lbl_progress.config(
                                        text=u"[Multicore %d/%d] '%s' carregada com sucesso!" % (c, t, s)
                                    ))
                                else:
                                    if err_msg:
                                        self.post_to_gui(lambda m=err_msg, s=short_name: messagebox.showwarning(
                                            "Aviso ArcMap", 
                                            u"Falha ao carregar '%s': %s" % (s, m), 
                                            parent=self.root
                                        ))
                    else:
                        # Carregar cada imagem sequencialmente
                        for idx, img_id in enumerate(image_ids):
                            short_name = img_id.split('/')[-1]
                            layer_title = "%s_%s" % (short_name, comp)
                            out_tif = os.path.join(tempfile.gettempdir(), "%s.tif" % layer_title)

                            prog_msg = "[Segundo Plano] Baixando %d de %d: %s..." % (idx + 1, total, short_name)
                            self.post_to_gui(lambda m=prog_msg: self.lbl_progress.config(text=m))

                            resp = gee_bridge.download_image(
                                image_ids=[img_id],
                                sensor=sensor,
                                comp_code=comp,
                                out_tif=out_tif,
                                custom_bands=custom_bands,
                                load_mode=load_mode,
                                bbox=bbox,
                                geojson_file=geojson_file,
                                scale=pixel_size
                            )

                            if resp.get('success'):
                                tif_file = resp.get('file')
                                self.post_to_gui(lambda s=short_name: self.lbl_progress.config(text="Carregando %s no TOC..." % s))
                                rep = gee_bridge.send_arcmap_command({
                                    'action': 'load_layer',
                                    'file': tif_file,
                                    'name': layer_title,
                                    'group': group_name,
                                    'zoom': auto_zoom if (idx == 0) else False,
                                    'comp': comp,
                                    'sensor': sensor,
                                    'custom_bands': custom_bands
                                }, timeout=120)
                                if rep.get('success'):
                                    loaded_count += 1
                                else:
                                    err_msg = rep.get('message', '')
                                    self.post_to_gui(lambda m=err_msg: messagebox.showwarning("Aviso ArcMap", "ArcMap retornou: " + m, parent=self.root))
                            else:
                                err_msg = resp.get('message', 'Erro ao baixar imagem.')
                                self.post_to_gui(lambda m=err_msg: messagebox.showerror("Erro de Download GEE", m, parent=self.root))

                def finish_all():
                    self.refresh_toc_rasters()
                    if replace_target:
                        if loaded_count > 0:
                            self.lbl_progress.config(text="Concluido! Camada '%s' substituida no ArcMap." % replace_target)
                            messagebox.showinfo("Substituicao Concluida", "Camada '%s' substituida com sucesso no TOC!" % replace_target, parent=self.root)
                        else:
                            self.lbl_progress.config(text="Falha na substituicao da camada.")
                            messagebox.showwarning("Falha", "Nenhuma imagem foi carregada para substituir a camada no TOC.", parent=self.root)
                    else:
                        if loaded_count > 0:
                            dest_info = ("ao grupo '%s'" % group_name) if group_name else "ao TOC"
                            msg = "%d imagem(ns) carregada(s) %s com sucesso em RGB!" % (loaded_count, dest_info)
                            self.lbl_progress.config(text="Concluido! " + msg)
                            messagebox.showinfo("Carregamento Concluido", msg, parent=self.root)
                        else:
                            self.lbl_progress.config(text="Nenhuma imagem adicionada ao TOC.")
                            messagebox.showwarning("Aviso", "Nenhuma imagem foi adicionada ao TOC. Verifique as mensagens de erro.", parent=self.root)

                self.post_to_gui(finish_all)
            except Exception as e:
                err_text = str(e)
                def on_err():
                    messagebox.showerror("Erro no Processo", err_text, parent=self.root)
                    self.lbl_progress.config(text="Erro: " + err_text[:60])
                self.post_to_gui(on_err)
            finally:
                def cleanup():
                    self.is_downloading = False
                    self.btn_add_toc.config(state=tk.NORMAL)
                    self.btn_mosaic_toc.config(state=tk.NORMAL)
                    if hasattr(self, 'btn_replace_toc'):
                        self.btn_replace_toc.config(state=tk.NORMAL)
                    if hasattr(self, 'btn_apply_comp_toc'):
                        self.btn_apply_comp_toc.config(state=tk.NORMAL)
                self.post_to_gui(cleanup)

        threading.Thread(target=worker).start()

def main():
    win = GEEPluginWindow()
    win.root.mainloop()

if __name__ == "__main__":
    main()
