"""
REVISOR_GUI.PY - Interfaz Gráfica para Revisión de Productos
Permite revisar, editar y aprobar productos de forma visual antes de exportar a WooCommerce.

Uso:
    python revisor_gui.py
    python revisor_gui.py data/processed/maestro_revision_*.xlsx
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys
import os


class ProductReviewerGUI:
    """Interfaz gráfica para revisión de productos."""
    
    # Columnas de atributos WooCommerce (hasta 6)
    ATTR_COLS = [
        ('Nombre del atributo 1', 'Valor(es) del atributo 1', 'Atributo visible 1'),
        ('Nombre del atributo 2', 'Valor(es) del atributo 2', 'Atributo visible 2'),
        ('Nombre del atributo 3', 'Valor(es) del atributo 3', 'Atributo visible 3'),
        ('Nombre del atributo 4', 'Valor(es) del atributo 4', 'Atributo visible 4'),
        ('Nombre del atributo 5', 'Valor(es) del atributo 5', 'Atributo visible 5'),
        ('Nombre del atributo 6', 'Valor(es) del atributo 6', 'Atributo visible 6'),
    ]
    
    def __init__(self, root):
        self.root = root
        self.root.title("📦 Revisor de Productos WooCommerce")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 700)
        
        # Estado
        self.df = None
        self.file_path = None
        self.modified = False
        self.selected_idx = None
        
        # Configurar estilo
        self.setup_styles()
        
        # Crear interfaz
        self.create_menu()
        self.create_main_layout()
        self.create_status_bar()
        
        # Cargar archivo si se pasó como argumento
        if len(sys.argv) > 1:
            self.load_file(sys.argv[1])
        else:
            # Buscar archivo más reciente
            latest = self.find_latest_file()
            if latest:
                self.load_file(latest)
    
    def setup_styles(self):
        """Configura estilos visuales."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores
        self.colors = {
            'bg': '#f5f5f5',
            'primary': '#2196F3',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'danger': '#f44336',
            'simple': '#81C784',
            'variable': '#64B5F6',
            'variation': '#FFB74D',
        }
        
        # Configurar estilos
        style.configure('Primary.TButton', padding=10)
        style.configure('Success.TButton', padding=10)
        style.configure('Danger.TButton', padding=10)
        
        style.configure('Simple.TLabel', background=self.colors['simple'], padding=5)
        style.configure('Variable.TLabel', background=self.colors['variable'], padding=5)
        style.configure('Variation.TLabel', background=self.colors['variation'], padding=5)
        
        # Treeview
        style.configure('Treeview', rowheight=28, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
    
    def create_menu(self):
        """Crea menú principal."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 Archivo", menu=file_menu)
        file_menu.add_command(label="Abrir...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Guardar", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Guardar como...", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exportar WooCommerce CSV", command=self.export_woocommerce)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.on_closing)
        
        # Editar
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="✏️ Editar", menu=edit_menu)
        edit_menu.add_command(label="Aprobar seleccionado", command=self.approve_selected, accelerator="Ctrl+A")
        edit_menu.add_command(label="Rechazar seleccionado", command=self.reject_selected)
        edit_menu.add_separator()
        edit_menu.add_command(label="Aprobar todos visibles", command=self.approve_all_visible)
        
        # Ver
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁️ Ver", menu=view_menu)
        view_menu.add_command(label="Todos", command=lambda: self.filter_products('all'))
        view_menu.add_command(label="Solo simples", command=lambda: self.filter_products('simple'))
        view_menu.add_command(label="Solo variables", command=lambda: self.filter_products('variable'))
        view_menu.add_command(label="Solo variaciones", command=lambda: self.filter_products('variation'))
        view_menu.add_separator()
        view_menu.add_command(label="Pendientes", command=lambda: self.filter_products('pending'))
        view_menu.add_command(label="Aprobados", command=lambda: self.filter_products('approved'))
        
        # Grupos
        group_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👨‍👧‍👦 Grupos", menu=group_menu)
        group_menu.add_command(label="Crear grupo desde selección", command=self.create_group_from_selection)
        group_menu.add_command(label="Agregar a grupo existente", command=self.add_to_existing_group)
        group_menu.add_separator()
        group_menu.add_command(label="Separar del grupo", command=self.remove_from_group)
        group_menu.add_command(label="🗑️ Eliminar grupo completo", command=self.delete_group)
        
        # Atajos de teclado
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-a>', lambda e: self.approve_selected())
        self.root.bind('<Delete>', lambda e: self.delete_selected())
    
    def create_main_layout(self):
        """Crea layout principal."""
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel izquierdo - Lista de productos
        left_panel = ttk.Frame(main_frame, width=500)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_panel.pack_propagate(False)
        
        self.create_product_list(left_panel)
        
        # Separador
        ttk.Separator(main_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Panel derecho - Detalle y edición
        right_panel = ttk.Frame(main_frame, width=600)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        right_panel.pack_propagate(False)
        
        self.create_detail_panel(right_panel)
    
    def create_product_list(self, parent):
        """Crea panel de lista de productos."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text="📦 Productos", font=('Segoe UI', 14, 'bold')).pack(side=tk.LEFT)
        
        # Botones de acción rápida
        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="✓ Aprobar", command=self.approve_selected, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✗ Rechazar", command=self.reject_selected, width=10).pack(side=tk.LEFT, padx=2)
        
        # Barra de búsqueda y filtros
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_by_search())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Filtro por tipo
        self.filter_var = tk.StringVar(value='all')
        filter_combo = ttk.Combobox(search_frame, textvariable=self.filter_var, 
                                    values=['all', 'simple', 'variable', 'variation', 'pending', 'approved'],
                                    width=12, state='readonly')
        filter_combo.pack(side=tk.RIGHT)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        
        # Treeview de productos
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('tipo', 'sku', 'nombre', 'precio', 'estado')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='extended')
        
        # Configurar columnas
        self.tree.heading('tipo', text='Tipo')
        self.tree.heading('sku', text='SKU')
        self.tree.heading('nombre', text='Nombre')
        self.tree.heading('precio', text='Precio')
        self.tree.heading('estado', text='Estado')
        
        self.tree.column('tipo', width=80, anchor='center')
        self.tree.column('sku', width=120)
        self.tree.column('nombre', width=200)
        self.tree.column('precio', width=80, anchor='e')
        self.tree.column('estado', width=70, anchor='center')
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Eventos
        self.tree.bind('<<TreeviewSelect>>', self.on_product_select)
        self.tree.bind('<Double-1>', self.on_product_double_click)
        
        # Tags para colores
        self.tree.tag_configure('simple', background='#E8F5E9')
        self.tree.tag_configure('variable', background='#E3F2FD')
        self.tree.tag_configure('variation', background='#FFF3E0')
        self.tree.tag_configure('approved', background='#C8E6C9')
        self.tree.tag_configure('pending', background='#FFECB3')
        
        # Resumen
        self.summary_label = ttk.Label(parent, text="", font=('Segoe UI', 9))
        self.summary_label.pack(fill=tk.X, pady=(10, 0))
    
    def create_detail_panel(self, parent):
        """Crea panel de detalle y edición."""
        # Notebook para pestañas
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Datos básicos
        basic_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(basic_tab, text="📝 Datos Básicos")
        self.create_basic_fields(basic_tab)
        
        # Tab 2: Atributos
        attr_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(attr_tab, text="🏷️ Atributos")
        self.create_attributes_panel(attr_tab)
        
        # Tab 3: Grupo/Variaciones
        group_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(group_tab, text="👨‍👧‍👦 Grupo")
        self.create_group_panel(group_tab)
        
        # Botones de acción
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(action_frame, text="💾 Guardar Cambios", command=self.save_current_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="↩️ Descartar", command=self.reload_current_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="✓ Aprobar", command=self.approve_selected).pack(side=tk.RIGHT, padx=5)
    
    def create_basic_fields(self, parent):
        """Crea campos básicos de edición."""
        # Frame con scroll
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.basic_frame = ttk.Frame(canvas)
        
        self.basic_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.basic_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Variables para campos
        self.field_vars = {}
        self.field_entries = []  # Para navegación con Enter
        
        fields = [
            ('ID', 'ID', False),
            ('Tipo', 'Tipo', False),
            ('SKU', 'SKU', True),
            ('Nombre', 'Nombre', True),
            ('Descripción corta', 'Descripción corta', True),
            ('Categorías', 'Categorías', True),
            ('Marcas', 'Marcas', True),
            ('Precio normal', 'Precio normal', True),
            ('Precio de oferta', 'Precio de oferta', True),
            ('Inventario', 'Inventario', True),
            ('Cantidad de bajo inventario', 'Cantidad de bajo inventario', True),
            ('Principal', 'Principal', False),
            ('Revisado_Humano', 'Revisado_Humano', False),
            ('Notas_Revisión', 'Notas_Revisión', True),
        ]
        
        for i, (label, field, editable) in enumerate(fields):
            ttk.Label(self.basic_frame, text=f"{label}:", font=('Segoe UI', 10, 'bold')).grid(
                row=i, column=0, sticky='w', pady=3, padx=5
            )
            
            var = tk.StringVar()
            self.field_vars[field] = var
            
            if editable:
                entry = ttk.Entry(self.basic_frame, textvariable=var, width=50)
                entry.grid(row=i, column=1, sticky='ew', pady=3, padx=5)
                
                # Bind Enter para ir al siguiente campo
                entry.bind('<Return>', lambda e, idx=len(self.field_entries): self.focus_next_basic_field(idx))
                # Bind para auto-guardar al perder foco
                entry.bind('<FocusOut>', lambda e: self.auto_save_basic_fields())
                
                self.field_entries.append(entry)
            else:
                label_widget = ttk.Label(self.basic_frame, textvariable=var, 
                                        background='#f0f0f0', width=50, anchor='w')
                label_widget.grid(row=i, column=1, sticky='ew', pady=3, padx=5)
        
        self.basic_frame.columnconfigure(1, weight=1)
    
    def create_attributes_panel(self, parent):
        """Crea panel de edición de atributos."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text="Atributos del Producto", font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)
        ttk.Button(header, text="💾 Guardar", command=self.save_current_product).pack(side=tk.RIGHT, padx=5)
        ttk.Button(header, text="➕ Agregar", command=self.add_attribute).pack(side=tk.RIGHT)
        
        # Frame con scroll para atributos
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.attr_scroll_frame = ttk.Frame(canvas)
        
        self.attr_scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.attr_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Variables y entries para atributos
        self.attr_vars = []
        self.attr_entries = []  # Para manejar navegación con Enter
        
        for i in range(6):
            frame = ttk.LabelFrame(self.attr_scroll_frame, text=f"Atributo {i+1}", padding=10)
            frame.pack(fill=tk.X, pady=5, padx=5)
            
            vars_dict = {
                'name': tk.StringVar(),
                'value': tk.StringVar(),
                'visible': tk.IntVar(value=1),
            }
            entries_dict = {}
            
            # Nombre
            name_frame = ttk.Frame(frame)
            name_frame.pack(fill=tk.X, pady=2)
            ttk.Label(name_frame, text="Nombre:", width=10).pack(side=tk.LEFT)
            name_entry = ttk.Entry(name_frame, textvariable=vars_dict['name'], width=40)
            name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entries_dict['name'] = name_entry
            
            # Valor
            val_frame = ttk.Frame(frame)
            val_frame.pack(fill=tk.X, pady=2)
            ttk.Label(val_frame, text="Valor(es):", width=10).pack(side=tk.LEFT)
            val_entry = ttk.Entry(val_frame, textvariable=vars_dict['value'], width=40)
            val_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entries_dict['value'] = val_entry
            
            # Visible + botones
            opt_frame = ttk.Frame(frame)
            opt_frame.pack(fill=tk.X, pady=2)
            ttk.Checkbutton(opt_frame, text="Visible", variable=vars_dict['visible']).pack(side=tk.LEFT)
            ttk.Button(opt_frame, text="🗑️", width=3, 
                      command=lambda idx=i: self.clear_attribute(idx)).pack(side=tk.RIGHT)
            
            # Bind Enter para navegación
            name_entry.bind('<Return>', lambda e, idx=i: self.focus_next_attr_field(idx, 'value'))
            val_entry.bind('<Return>', lambda e, idx=i: self.focus_next_attr_field(idx, 'next'))
            
            # Bind para auto-guardar al perder foco
            name_entry.bind('<FocusOut>', lambda e: self.auto_save_attributes())
            val_entry.bind('<FocusOut>', lambda e: self.auto_save_attributes())
            
            self.attr_vars.append(vars_dict)
            self.attr_entries.append(entries_dict)
    
    def focus_next_attr_field(self, current_idx: int, field: str):
        """Mueve el foco al siguiente campo de atributo."""
        if field == 'value':
            # Ir al campo valor del mismo atributo
            self.attr_entries[current_idx]['value'].focus_set()
        elif field == 'next':
            # Ir al campo nombre del siguiente atributo
            next_idx = current_idx + 1
            if next_idx < len(self.attr_entries):
                self.attr_entries[next_idx]['name'].focus_set()
            else:
                # Si es el último, guardar y volver al primero
                self.save_current_product()
                self.attr_entries[0]['name'].focus_set()
    
    def auto_save_attributes(self):
        """Auto-guarda atributos cuando se pierde el foco."""
        if self.selected_idx is None or self.df is None:
            return
        
        idx = self.selected_idx
        
        # Verificar que el índice existe
        if idx not in self.df.index:
            return
        
        try:
            row = self.df.loc[idx]
            tipo = row.get('Tipo', '')
            
            # Obtener hijos si es padre (para propagar cambios)
            children_idx = []
            if tipo == 'variable':
                parent_id = row['ID']
                children = self.df[self.df['Principal'] == f'id:{parent_id}']
                children_idx = children.index.tolist()
            
            # Guardar atributos
            for i, (name_col, val_col, vis_col) in enumerate(self.ATTR_COLS):
                new_name = self.attr_vars[i]['name'].get().strip()
                new_value = self.attr_vars[i]['value'].get().strip()
                new_visible = self.attr_vars[i]['visible'].get()
                
                # Guardar en producto actual
                try:
                    self.df.at[idx, name_col] = new_name if new_name else ''
                    self.df.at[idx, val_col] = new_value if new_value else ''
                    self.df.at[idx, vis_col] = int(new_visible)
                except Exception:
                    pass
                
                # Si es padre, propagar nombre y visibilidad a hijos
                if tipo == 'variable' and children_idx:
                    for child_idx in children_idx:
                        try:
                            self.df.at[child_idx, name_col] = new_name if new_name else ''
                            self.df.at[child_idx, vis_col] = int(new_visible)
                        except Exception:
                            pass
            
            self.modified = True
            self.update_modified_indicator()
        except Exception:
            pass  # Ignorar errores durante auto-guardado
    
    def focus_next_basic_field(self, current_idx: int):
        """Mueve el foco al siguiente campo básico."""
        next_idx = current_idx + 1
        if next_idx < len(self.field_entries):
            self.field_entries[next_idx].focus_set()
        else:
            # Si es el último, guardar
            self.save_current_product()
            # Ir al primer campo
            if self.field_entries:
                self.field_entries[0].focus_set()
    
    def auto_save_basic_fields(self):
        """Auto-guarda campos básicos cuando se pierde el foco."""
        if self.selected_idx is None or self.df is None:
            return
        
        idx = self.selected_idx
        
        # Verificar que el índice existe
        if idx not in self.df.index:
            return
        
        # Campos numéricos que requieren conversión
        numeric_fields = ['Precio normal', 'Precio de oferta', 'Inventario', 'Cantidad de bajo inventario']
        
        # Guardar campos básicos editables
        editable_fields = ['SKU', 'Nombre', 'Descripción corta', 'Categorías', 'Marcas',
                          'Precio normal', 'Precio de oferta', 'Inventario', 
                          'Cantidad de bajo inventario', 'Notas_Revisión']
        
        for field in editable_fields:
            if field in self.field_vars:
                value = self.field_vars[field].get().strip()
                
                # Manejar campos numéricos
                if field in numeric_fields:
                    if value == '' or value.lower() == 'nan':
                        value = None  # Usar None para NaN
                    else:
                        try:
                            value = float(value)
                        except ValueError:
                            value = None
                
                try:
                    self.df.at[idx, field] = value
                except Exception:
                    pass  # Ignorar errores de tipo
        
        self.modified = True
        self.update_modified_indicator()
    
    def create_group_panel(self, parent):
        """Crea panel de grupos y variaciones."""
        # Info del grupo
        self.group_info_frame = ttk.LabelFrame(parent, text="Información del Grupo", padding=10)
        self.group_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.group_info_label = ttk.Label(self.group_info_frame, text="Selecciona un producto para ver información del grupo")
        self.group_info_label.pack()
        
        # Lista de variaciones
        var_frame = ttk.LabelFrame(parent, text="Variaciones", padding=10)
        var_frame.pack(fill=tk.BOTH, expand=True)
        
        # Botones
        btn_frame = ttk.Frame(var_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(btn_frame, text="➕ Agregar variación", command=self.add_variation).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="➖ Quitar del grupo", command=self.remove_variation).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ Eliminar grupo", command=self.delete_group).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_frame, text="✏️ Renombrar grupo", command=self.rename_group).pack(side=tk.RIGHT, padx=2)
        
        # Treeview de variaciones
        columns = ('sku', 'nombre', 'precio', 'atributos')
        self.var_tree = ttk.Treeview(var_frame, columns=columns, show='headings', height=8)
        
        self.var_tree.heading('sku', text='SKU')
        self.var_tree.heading('nombre', text='Nombre')
        self.var_tree.heading('precio', text='Precio')
        self.var_tree.heading('atributos', text='Atributos')
        
        self.var_tree.column('sku', width=100)
        self.var_tree.column('nombre', width=200)
        self.var_tree.column('precio', width=80)
        self.var_tree.column('atributos', width=150)
        
        vsb = ttk.Scrollbar(var_frame, orient="vertical", command=self.var_tree.yview)
        self.var_tree.configure(yscrollcommand=vsb.set)
        
        self.var_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Doble clic para navegar a la variación
        self.var_tree.bind('<Double-1>', self.on_variation_double_click)
    
    def on_variation_double_click(self, event):
        """Navega al producto cuando se hace doble clic en una variación."""
        selection = self.var_tree.selection()
        if selection:
            idx = int(selection[0])
            # Buscar en el treeview principal y seleccionar
            if str(idx) in self.tree.get_children():
                self.tree.selection_set(str(idx))
                self.tree.see(str(idx))
                self.tree.focus(str(idx))
                # Cargar detalles
                self.selected_idx = idx
                self.load_product_details(idx)
            else:
                # Si no está visible (por filtro), mostrar mensaje
                messagebox.showinfo("Info", "El producto no está visible con el filtro actual. Cambia a 'Todos' para verlo.")
    
    def create_status_bar(self):
        """Crea barra de estado."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(self.status_bar, text="Listo", anchor='w')
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.modified_label = ttk.Label(self.status_bar, text="", anchor='e')
        self.modified_label.pack(side=tk.RIGHT, padx=10)
    
    # ===== Carga y guardado de archivos =====
    
    def find_latest_file(self):
        """Encuentra el archivo maestro más reciente."""
        dir_path = Path('data/processed')
        if not dir_path.exists():
            return None
        
        files = list(dir_path.glob('maestro_revision_*.xlsx'))
        if not files:
            files = list(dir_path.glob('maestro_revision_*.csv'))
        
        if not files:
            return None
        
        return str(max(files, key=lambda f: f.stat().st_mtime))
    
    def open_file(self):
        """Abre diálogo para seleccionar archivo."""
        file_path = filedialog.askopenfilename(
            title="Abrir archivo de revisión",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ],
            initialdir="data/processed"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        """Carga un archivo de revisión."""
        try:
            path = Path(file_path)
            
            if path.suffix.lower() == '.csv':
                self.df = pd.read_csv(path, encoding='utf-8')
            else:
                self.df = pd.read_excel(path, sheet_name='Maestro')
            
            # Asegurar columnas necesarias
            if 'Revisado_Humano' not in self.df.columns:
                self.df['Revisado_Humano'] = 'No'
            if 'Notas_Revisión' not in self.df.columns:
                self.df['Notas_Revisión'] = ''
            
            # Asegurar columnas de atributos
            for name_col, val_col, vis_col in self.ATTR_COLS:
                for col in [name_col, val_col, vis_col]:
                    if col not in self.df.columns:
                        self.df[col] = ''
            
            self.file_path = path
            self.modified = False
            
            self.refresh_product_list()
            self.update_status(f"Cargado: {path.name}")
            self.root.title(f"📦 Revisor de Productos - {path.name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")
    
    def save_file(self):
        """Guarda el archivo actual."""
        if self.df is None or self.file_path is None:
            return
        
        try:
            # Guardar Excel
            xlsx_path = self.file_path.with_suffix('.xlsx')
            with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
                self.df.to_excel(writer, sheet_name='Maestro', index=False)
            
            # Guardar CSV
            csv_path = self.file_path.with_suffix('.csv')
            self.df.to_csv(csv_path, index=False, encoding='utf-8')
            
            self.modified = False
            self.update_status(f"Guardado: {xlsx_path.name}")
            self.update_modified_indicator()
            
            messagebox.showinfo("Guardado", f"Archivo guardado correctamente:\n{xlsx_path.name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")
    
    def save_as(self):
        """Guarda con nuevo nombre."""
        file_path = filedialog.asksaveasfilename(
            title="Guardar como",
            defaultextension=".xlsx",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
            ],
            initialdir="data/processed"
        )
        
        if file_path:
            self.file_path = Path(file_path)
            self.save_file()
    
    def export_woocommerce(self):
        """Exporta CSV para WooCommerce."""
        if self.df is None:
            messagebox.showwarning("Aviso", "No hay datos para exportar")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Exportar CSV WooCommerce",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir="data/processed",
            initialfile=f"woocommerce_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if file_path:
            try:
                # Excluir columnas de auditoría
                exclude_cols = ['SKU_Original', 'Confianza_Automática', 'Revisado_Humano', 'Notas_Revisión']
                woo_cols = [col for col in self.df.columns if col not in exclude_cols]
                woo_df = self.df[woo_cols]
                woo_df.to_csv(file_path, index=False, encoding='utf-8')
                
                messagebox.showinfo("Exportado", f"CSV WooCommerce exportado:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al exportar:\n{e}")
    
    # ===== Lista de productos =====
    
    def refresh_product_list(self):
        """Actualiza la lista de productos."""
        if self.df is None:
            return
        
        # Limpiar
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Aplicar filtros
        filtered_df = self.get_filtered_df()
        
        # Poblar
        for idx, row in filtered_df.iterrows():
            tipo = row.get('Tipo', '')
            sku = row.get('SKU', '')
            nombre = str(row.get('Nombre', ''))[:50]
            precio = row.get('Precio normal', '')
            revisado = row.get('Revisado_Humano', 'No')
            
            estado = '✓' if revisado == 'Sí' else '○'
            
            # Determinar tag
            tags = [tipo]
            if revisado == 'Sí':
                tags.append('approved')
            else:
                tags.append('pending')
            
            self.tree.insert('', 'end', iid=str(idx), values=(tipo, sku, nombre, precio, estado), tags=tags)
        
        # Actualizar resumen
        self.update_summary()
    
    def get_filtered_df(self):
        """Aplica filtros al DataFrame."""
        if self.df is None:
            return pd.DataFrame()
        
        df = self.df.copy()
        
        # Filtro por tipo
        filter_type = self.filter_var.get()
        if filter_type == 'simple':
            df = df[df['Tipo'] == 'simple']
        elif filter_type == 'variable':
            df = df[df['Tipo'] == 'variable']
        elif filter_type == 'variation':
            df = df[df['Tipo'] == 'variation']
        elif filter_type == 'pending':
            df = df[df['Revisado_Humano'] != 'Sí']
        elif filter_type == 'approved':
            df = df[df['Revisado_Humano'] == 'Sí']
        
        # Filtro por búsqueda
        search = self.search_var.get().strip().upper()
        if search:
            mask = (
                df['SKU'].astype(str).str.upper().str.contains(search, na=False) |
                df['Nombre'].astype(str).str.upper().str.contains(search, na=False)
            )
            df = df[mask]
        
        return df
    
    def apply_filters(self):
        """Aplica filtros y actualiza lista."""
        self.refresh_product_list()
    
    def filter_by_search(self):
        """Filtra por texto de búsqueda."""
        self.refresh_product_list()
    
    def filter_products(self, filter_type: str):
        """Cambia el filtro activo."""
        self.filter_var.set(filter_type)
        self.refresh_product_list()
    
    def update_summary(self):
        """Actualiza el resumen de productos."""
        if self.df is None:
            return
        
        total = len(self.df)
        simples = (self.df['Tipo'] == 'simple').sum()
        variables = (self.df['Tipo'] == 'variable').sum()
        variations = (self.df['Tipo'] == 'variation').sum()
        approved = (self.df['Revisado_Humano'] == 'Sí').sum()
        
        filtered = len(self.get_filtered_df())
        
        text = f"Total: {total} | Simples: {simples} | Variables: {variables} | Variaciones: {variations} | "
        text += f"Aprobados: {approved}/{total} | Mostrando: {filtered}"
        
        self.summary_label.config(text=text)
    
    # ===== Selección y edición =====
    
    def on_product_select(self, event):
        """Maneja selección de producto."""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Auto-guardar producto anterior antes de cambiar
        if self.selected_idx is not None and self.df is not None:
            self.auto_save_basic_fields()
            self.auto_save_attributes()
        
        idx = int(selection[0])
        self.selected_idx = idx
        self.load_product_details(idx)
    
    def on_product_double_click(self, event):
        """Maneja doble clic en producto."""
        # Ir a la pestaña de edición
        self.notebook.select(0)
    
    def load_product_details(self, idx: int):
        """Carga detalles del producto seleccionado."""
        if self.df is None or idx not in self.df.index:
            return
        
        row = self.df.loc[idx]
        
        # Cargar campos básicos
        for field, var in self.field_vars.items():
            value = row.get(field, '')
            if pd.isna(value):
                value = ''
            var.set(str(value))
        
        # Cargar atributos
        for i, (name_col, val_col, vis_col) in enumerate(self.ATTR_COLS):
            name = row.get(name_col, '')
            value = row.get(val_col, '')
            visible = row.get(vis_col, 1)
            
            self.attr_vars[i]['name'].set('' if pd.isna(name) else str(name))
            self.attr_vars[i]['value'].set('' if pd.isna(value) else str(value))
            # Manejar visible: puede ser NaN, string vacío o número
            if pd.isna(visible) or visible == '':
                vis_val = 1
            else:
                try:
                    vis_val = int(float(visible))
                except (ValueError, TypeError):
                    vis_val = 1
            self.attr_vars[i]['visible'].set(vis_val)
        
        # Cargar info del grupo
        self.load_group_info(idx)
    
    def load_group_info(self, idx: int):
        """Carga información del grupo."""
        if self.df is None:
            return
        
        row = self.df.loc[idx]
        tipo = row.get('Tipo', '')
        
        # Limpiar variaciones
        for item in self.var_tree.get_children():
            self.var_tree.delete(item)
        
        # Configurar tag para highlight
        self.var_tree.tag_configure('selected', background='#90CAF9', foreground='black')
        self.var_tree.tag_configure('normal', background='', foreground='')
        
        if tipo == 'variable':
            # Es padre - mostrar hijos
            parent_id = row['ID']
            children = self.df[self.df['Principal'] == f'id:{parent_id}']
            
            self.group_info_label.config(text=f"👨‍👧‍👦 Padre: {row['Nombre'][:50]}\n📊 Variaciones: {len(children)}")
            
            for child_idx, child in children.iterrows():
                attrs = []
                for name_col, val_col, _ in self.ATTR_COLS:
                    name = child.get(name_col, '')
                    val = child.get(val_col, '')
                    if pd.notna(name) and name:
                        attrs.append(f"{name}={val}")
                
                self.var_tree.insert('', 'end', iid=str(child_idx), values=(
                    child.get('SKU', ''),
                    str(child.get('Nombre', ''))[:40],
                    child.get('Precio normal', ''),
                    ', '.join(attrs[:2])
                ), tags=('normal',))
        
        elif tipo == 'variation':
            # Es hijo - buscar padre y mostrar todo el grupo
            principal = row.get('Principal', '')
            if 'id:' in str(principal):
                parent_id = int(str(principal).replace('id:', ''))
                parent_df = self.df[self.df['ID'] == parent_id]
                
                if len(parent_df) > 0:
                    parent = parent_df.iloc[0]
                    parent_idx = parent_df.index[0]
                    
                    # Buscar todas las variaciones del mismo padre
                    siblings = self.df[self.df['Principal'] == f'id:{parent_id}']
                    
                    self.group_info_label.config(
                        text=f"👨‍👧‍👦 Padre: {parent['Nombre'][:50]}\n"
                             f"📊 Variaciones: {len(siblings)} | 🔍 Seleccionada: {row['Nombre'][:30]}"
                    )
                    
                    # Mostrar todas las variaciones, resaltando la actual
                    for sib_idx, sibling in siblings.iterrows():
                        attrs = []
                        for name_col, val_col, _ in self.ATTR_COLS:
                            name = sibling.get(name_col, '')
                            val = sibling.get(val_col, '')
                            if pd.notna(name) and name:
                                attrs.append(f"{name}={val}")
                        
                        # Determinar si es la variación seleccionada
                        is_selected = (sib_idx == idx)
                        tag = 'selected' if is_selected else 'normal'
                        
                        self.var_tree.insert('', 'end', iid=str(sib_idx), values=(
                            sibling.get('SKU', ''),
                            str(sibling.get('Nombre', ''))[:40],
                            sibling.get('Precio normal', ''),
                            ', '.join(attrs[:2])
                        ), tags=(tag,))
                    
                    # Hacer scroll a la variación seleccionada y seleccionarla
                    self.var_tree.selection_set(str(idx))
                    self.var_tree.see(str(idx))
                else:
                    self.group_info_label.config(text="⚠️ Variación huérfana (padre no encontrado)")
            else:
                self.group_info_label.config(text="⚠️ Variación sin referencia a padre")
        
        else:
            self.group_info_label.config(text="📦 Producto simple (sin grupo)")
    
    def save_current_product(self):
        """Guarda cambios del producto actual."""
        if self.selected_idx is None or self.df is None:
            return
        
        idx = self.selected_idx
        
        # Verificar que el índice existe
        if idx not in self.df.index:
            return
        
        # Campos numéricos que requieren conversión
        numeric_fields = ['Precio normal', 'Precio de oferta', 'Inventario', 'Cantidad de bajo inventario']
        
        # Guardar campos básicos editables
        editable_fields = ['SKU', 'Nombre', 'Descripción corta', 'Categorías', 'Marcas',
                          'Precio normal', 'Precio de oferta', 'Inventario', 
                          'Cantidad de bajo inventario', 'Notas_Revisión']
        
        for field in editable_fields:
            if field in self.field_vars:
                value = self.field_vars[field].get().strip()
                
                # Manejar campos numéricos
                if field in numeric_fields:
                    if value == '' or value.lower() == 'nan':
                        value = None
                    else:
                        try:
                            value = float(value)
                        except ValueError:
                            value = None
                
                try:
                    self.df.at[idx, field] = value
                except Exception:
                    pass
        
        # Guardar atributos
        for i, (name_col, val_col, vis_col) in enumerate(self.ATTR_COLS):
            try:
                self.df.at[idx, name_col] = self.attr_vars[i]['name'].get().strip()
                self.df.at[idx, val_col] = self.attr_vars[i]['value'].get().strip()
                self.df.at[idx, vis_col] = int(self.attr_vars[i]['visible'].get())
            except Exception:
                pass
        
        self.modified = True
        self.update_modified_indicator()
        self.refresh_product_list()
        
        # Re-seleccionar
        try:
            self.tree.selection_set(str(idx))
        except Exception:
            pass
        
        self.update_status("Producto actualizado")
    
    def reload_current_product(self):
        """Recarga datos del producto actual."""
        if self.selected_idx is not None:
            self.load_product_details(self.selected_idx)
            self.update_status("Cambios descartados")
    
    # ===== Acciones de productos =====
    
    def approve_selected(self):
        """Aprueba productos seleccionados."""
        selection = self.tree.selection()
        if not selection:
            return
        
        for item in selection:
            idx = int(item)
            self.df.at[idx, 'Revisado_Humano'] = 'Sí'
        
        self.modified = True
        self.update_modified_indicator()
        self.refresh_product_list()
        self.update_status(f"{len(selection)} producto(s) aprobado(s)")
    
    def reject_selected(self):
        """Rechaza productos seleccionados."""
        selection = self.tree.selection()
        if not selection:
            return
        
        note = simpledialog.askstring("Razón", "Razón del rechazo (opcional):")
        
        for item in selection:
            idx = int(item)
            self.df.at[idx, 'Revisado_Humano'] = 'No'
            if note:
                self.df.at[idx, 'Notas_Revisión'] = note
        
        self.modified = True
        self.update_modified_indicator()
        self.refresh_product_list()
        self.update_status(f"{len(selection)} producto(s) rechazado(s)")
    
    def approve_all_visible(self):
        """Aprueba todos los productos visibles."""
        filtered_df = self.get_filtered_df()
        
        if len(filtered_df) == 0:
            return
        
        if messagebox.askyesno("Confirmar", f"¿Aprobar {len(filtered_df)} productos?"):
            for idx in filtered_df.index:
                self.df.at[idx, 'Revisado_Humano'] = 'Sí'
            
            self.modified = True
            self.update_modified_indicator()
            self.refresh_product_list()
            self.update_status(f"{len(filtered_df)} productos aprobados")
    
    def delete_selected(self):
        """Elimina productos seleccionados."""
        selection = self.tree.selection()
        if not selection:
            return
        
        if not messagebox.askyesno("Confirmar", f"¿Eliminar {len(selection)} producto(s)?"):
            return
        
        indices = [int(item) for item in selection]
        self.df = self.df.drop(indices).reset_index(drop=True)
        self.df['ID'] = range(1, len(self.df) + 1)
        
        self.modified = True
        self.update_modified_indicator()
        self.refresh_product_list()
        self.selected_idx = None
        self.update_status(f"{len(indices)} producto(s) eliminado(s)")
    
    # ===== Atributos =====
    
    def add_attribute(self):
        """Agrega un nuevo atributo."""
        # Encontrar siguiente slot vacío
        for i, vars_dict in enumerate(self.attr_vars):
            if not vars_dict['name'].get():
                # Enfocar este atributo
                messagebox.showinfo("Info", f"Usa el Atributo {i+1} para agregar un nuevo atributo")
                return
        
        messagebox.showwarning("Aviso", "No hay slots de atributos disponibles (máximo 6)")
    
    def clear_attribute(self, idx: int):
        """Limpia un atributo."""
        self.attr_vars[idx]['name'].set('')
        self.attr_vars[idx]['value'].set('')
        self.attr_vars[idx]['visible'].set(1)
    
    # ===== Grupos =====
    
    def add_variation(self):
        """Agrega una variación al grupo actual."""
        if self.selected_idx is None:
            return
        
        row = self.df.loc[self.selected_idx]
        if row.get('Tipo') != 'variable':
            messagebox.showwarning("Aviso", "Selecciona un producto padre (variable) primero")
            return
        
        # Obtener productos simples
        simples = self.df[self.df['Tipo'] == 'simple']
        
        if len(simples) == 0:
            messagebox.showinfo("Info", "No hay productos simples disponibles")
            return
        
        # Crear diálogo de selección con buscador
        dialog = tk.Toplevel(self.root)
        dialog.title("Agregar variación")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Información del grupo
        ttk.Label(dialog, text=f"Grupo: {row['Nombre'][:50]}", 
                 font=('Segoe UI', 11, 'bold')).pack(pady=(10, 5))
        
        # Frame de búsqueda
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="🔍 Buscar:").pack(side=tk.LEFT, padx=(0, 5))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Contador de resultados
        count_label = ttk.Label(dialog, text=f"Mostrando {len(simples)} productos simples")
        count_label.pack(pady=5)
        
        # Listbox con scroll
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, font=('Segoe UI', 10))
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Variable para mapear índice de listbox a índice de DataFrame
        idx_map = {}
        
        def populate_list(filter_text=""):
            """Rellena la lista con productos filtrados."""
            listbox.delete(0, tk.END)
            idx_map.clear()
            
            filter_text = filter_text.lower().strip()
            count = 0
            
            for idx, simple in simples.iterrows():
                sku = str(simple.get('SKU', ''))
                nombre = str(simple.get('Nombre', ''))
                
                # Filtrar por texto de búsqueda
                if filter_text:
                    if filter_text not in sku.lower() and filter_text not in nombre.lower():
                        continue
                
                listbox.insert(tk.END, f"{sku} - {nombre[:45]}")
                idx_map[count] = idx
                count += 1
            
            count_label.config(text=f"Mostrando {count} de {len(simples)} productos simples")
        
        def on_search(*args):
            """Callback cuando cambia el texto de búsqueda."""
            populate_list(search_var.get())
        
        # Vincular búsqueda
        search_var.trace('w', on_search)
        
        # Poblar lista inicial
        populate_list()
        
        # Enfocar campo de búsqueda
        search_entry.focus_set()
        
        def on_add():
            selections = listbox.curselection()
            if not selections:
                messagebox.showwarning("Aviso", "Selecciona al menos un producto")
                return
            
            parent_id = row['ID']
            added_count = 0
            for sel in selections:
                if sel in idx_map:
                    simple_idx = idx_map[sel]
                    self.df.at[simple_idx, 'Tipo'] = 'variation'
                    self.df.at[simple_idx, 'Principal'] = f'id:{parent_id}'
                    self.df.at[simple_idx, 'Clase de impuesto'] = 'parent'
                    added_count += 1
            
            self.modified = True
            self.update_modified_indicator()
            self.refresh_product_list()
            self.load_group_info(self.selected_idx)
            dialog.destroy()
            self.update_status(f"{added_count} variación(es) agregada(s)")
        
        # Frame de botones
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="✓ Agregar seleccionados", command=on_add).pack(side=tk.RIGHT, padx=5)
    
    def remove_variation(self):
        """Quita variación del grupo."""
        selection = self.var_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Selecciona una variación en la lista")
            return
        
        for item in selection:
            idx = int(item)
            self.df.at[idx, 'Tipo'] = 'simple'
            self.df.at[idx, 'Principal'] = ''
            self.df.at[idx, 'Clase de impuesto'] = ''
        
        self.modified = True
        self.update_modified_indicator()
        self.refresh_product_list()
        self.load_group_info(self.selected_idx)
        self.update_status(f"{len(selection)} variación(es) convertida(s) a simple")
    
    def rename_group(self):
        """Renombra el grupo."""
        if self.selected_idx is None:
            return
        
        row = self.df.loc[self.selected_idx]
        if row.get('Tipo') != 'variable':
            messagebox.showwarning("Aviso", "Selecciona un producto padre (variable)")
            return
        
        new_name = simpledialog.askstring("Renombrar", "Nuevo nombre para el grupo:", 
                                          initialvalue=row['Nombre'])
        if new_name:
            self.df.at[self.selected_idx, 'Nombre'] = new_name
            
            # Preguntar si actualizar hijos
            if messagebox.askyesno("Actualizar hijos", "¿Actualizar nombres de las variaciones?"):
                parent_id = row['ID']
                children = self.df[self.df['Principal'] == f'id:{parent_id}']
                
                for child_idx, child in children.iterrows():
                    # Construir nombre con atributos
                    attrs = []
                    for name_col, val_col, _ in self.ATTR_COLS:
                        val = child.get(val_col, '')
                        if pd.notna(val) and val:
                            attrs.append(str(val))
                    
                    if attrs:
                        self.df.at[child_idx, 'Nombre'] = f"{new_name} - {' '.join(attrs[:2])}"
                    else:
                        var_num = list(children.index).index(child_idx) + 1
                        self.df.at[child_idx, 'Nombre'] = f"{new_name} - Variante {var_num}"
            
            self.modified = True
            self.update_modified_indicator()
            self.refresh_product_list()
            self.load_product_details(self.selected_idx)
    
    def create_group_from_selection(self):
        """Crea un grupo desde la selección actual."""
        selection = self.tree.selection()
        if len(selection) < 2:
            messagebox.showwarning("Aviso", "Selecciona al menos 2 productos")
            return
        
        # Verificar que todos son simples
        indices = [int(item) for item in selection]
        for idx in indices:
            if self.df.loc[idx, 'Tipo'] != 'simple':
                messagebox.showwarning("Aviso", "Solo se pueden agrupar productos simples")
                return
        
        # Pedir nombre del grupo
        base_name = simpledialog.askstring("Nuevo grupo", "Nombre del grupo padre:")
        if not base_name:
            return
        
        # Crear padre
        max_id = self.df['ID'].max()
        new_id = max_id + 1
        
        import hashlib
        slug = base_name.lower().replace(' ', '-')[:16]
        token = hashlib.md5(slug.encode()).hexdigest()[:6].upper()
        new_sku = f"GRP-{slug.upper()}-{token}"
        
        sample = self.df.loc[indices[0]]
        
        # Crear fila del padre
        parent_data = {col: '' for col in self.df.columns}
        parent_data['ID'] = new_id
        parent_data['Tipo'] = 'variable'
        parent_data['SKU'] = new_sku
        parent_data['Nombre'] = base_name.upper()
        parent_data['Publicado'] = 0
        parent_data['Categorías'] = sample.get('Categorías', '')
        parent_data['Marcas'] = sample.get('Marcas', '')
        parent_data['Revisado_Humano'] = 'No'
        
        # Recopilar atributos
        for i, (name_col, val_col, vis_col) in enumerate(self.ATTR_COLS):
            all_names = set()
            all_vals = set()
            for idx in indices:
                name = self.df.loc[idx, name_col]
                val = self.df.loc[idx, val_col]
                if pd.notna(name) and name:
                    all_names.add(str(name))
                if pd.notna(val) and val:
                    all_vals.add(str(val))
            
            if all_names:
                parent_data[name_col] = list(all_names)[0]
                parent_data[val_col] = '|'.join(sorted(all_vals))
                parent_data[vis_col] = 1
        
        # Agregar padre
        parent_df = pd.DataFrame([parent_data])
        self.df = pd.concat([self.df, parent_df], ignore_index=True)
        
        # Actualizar hijos
        new_parent_idx = len(self.df) - 1
        actual_parent_id = self.df.loc[new_parent_idx, 'ID']
        
        for idx in indices:
            self.df.at[idx, 'Tipo'] = 'variation'
            self.df.at[idx, 'Principal'] = f'id:{actual_parent_id}'
            self.df.at[idx, 'Clase de impuesto'] = 'parent'
        
        self.modified = True
        self.update_modified_indicator()
        self.refresh_product_list()
        self.update_status(f"Grupo '{base_name}' creado con {len(indices)} variaciones")
    
    def add_to_existing_group(self):
        """Agrega selección a un grupo existente."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Selecciona productos para agregar")
            return
        
        # Obtener grupos
        groups = self.df[self.df['Tipo'] == 'variable']
        
        if len(groups) == 0:
            messagebox.showinfo("Info", "No hay grupos disponibles")
            return
        
        # Diálogo de selección de grupo con buscador
        dialog = tk.Toplevel(self.root)
        dialog.title("Seleccionar grupo destino")
        dialog.geometry("700x550")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # === Panel superior: Productos a agregar ===
        products_frame = ttk.LabelFrame(dialog, text=f"📦 Productos a agregar ({len(selection)})", padding=5)
        products_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        # Lista de productos seleccionados (máximo 5 visibles)
        products_list = tk.Listbox(products_frame, height=min(5, len(selection)), font=('Segoe UI', 9))
        if len(selection) > 5:
            prod_scroll = ttk.Scrollbar(products_frame, orient="vertical", command=products_list.yview)
            products_list.configure(yscrollcommand=prod_scroll.set)
            prod_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        products_list.pack(fill=tk.X, expand=True)
        
        for item in selection:
            idx = int(item)
            if idx in self.df.index:
                prod = self.df.loc[idx]
                sku = str(prod.get('SKU', ''))[:15]
                nombre = str(prod.get('Nombre', ''))[:50]
                products_list.insert(tk.END, f"{sku} - {nombre}")
        
        # === Panel de búsqueda de grupos ===
        ttk.Label(dialog, text="Selecciona el grupo destino:", 
                 font=('Segoe UI', 11, 'bold')).pack(pady=(10, 5))
        
        # Frame de búsqueda
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="🔍 Buscar grupo:").pack(side=tk.LEFT, padx=(0, 5))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Contador de resultados
        count_label = ttk.Label(dialog, text=f"Mostrando {len(groups)} grupos")
        count_label.pack(pady=5)
        
        # Listbox con scroll
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        listbox = tk.Listbox(frame, font=('Segoe UI', 10))
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Variable para mapear índice de listbox a índice de DataFrame
        idx_map = {}
        
        def populate_list(filter_text=""):
            """Rellena la lista con grupos filtrados."""
            listbox.delete(0, tk.END)
            idx_map.clear()
            
            filter_text = filter_text.lower().strip()
            count = 0
            
            for idx, group in groups.iterrows():
                sku = str(group.get('SKU', ''))
                nombre = str(group.get('Nombre', ''))
                
                # Contar variaciones del grupo
                parent_id = group['ID']
                var_count = len(self.df[self.df['Principal'] == f'id:{parent_id}'])
                
                # Filtrar por texto de búsqueda
                if filter_text:
                    if filter_text not in sku.lower() and filter_text not in nombre.lower():
                        continue
                
                listbox.insert(tk.END, f"{sku} - {nombre[:40]} ({var_count} var.)")
                idx_map[count] = idx
                count += 1
            
            count_label.config(text=f"Mostrando {count} de {len(groups)} grupos")
        
        def on_search(*args):
            """Callback cuando cambia el texto de búsqueda."""
            populate_list(search_var.get())
        
        # Vincular búsqueda
        search_var.trace('w', on_search)
        
        # Poblar lista inicial
        populate_list()
        
        # Enfocar campo de búsqueda
        search_entry.focus_set()
        
        def on_add():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Aviso", "Selecciona un grupo")
                return
            
            if sel[0] not in idx_map:
                return
            
            parent_idx = idx_map[sel[0]]
            parent_id = self.df.loc[parent_idx, 'ID']
            parent_name = self.df.loc[parent_idx, 'Nombre']
            
            for item in selection:
                idx = int(item)
                self.df.at[idx, 'Tipo'] = 'variation'
                self.df.at[idx, 'Principal'] = f'id:{parent_id}'
                self.df.at[idx, 'Clase de impuesto'] = 'parent'
            
            self.modified = True
            self.update_modified_indicator()
            self.refresh_product_list()
            dialog.destroy()
            self.update_status(f"{len(selection)} producto(s) agregado(s) al grupo '{parent_name[:30]}'")
        
        # Frame de botones
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="✓ Agregar al grupo", command=on_add).pack(side=tk.RIGHT, padx=5)
    
    def remove_from_group(self):
        """Separa producto seleccionado del grupo."""
        selection = self.tree.selection()
        if not selection:
            return
        
        count = 0
        for item in selection:
            idx = int(item)
            if self.df.loc[idx, 'Tipo'] == 'variation':
                self.df.at[idx, 'Tipo'] = 'simple'
                self.df.at[idx, 'Principal'] = ''
                self.df.at[idx, 'Clase de impuesto'] = ''
                count += 1
        
        if count > 0:
            self.modified = True
            self.update_modified_indicator()
            self.refresh_product_list()
            self.update_status(f"{count} variación(es) convertida(s) a simple")
    
    def delete_group(self):
        """Elimina un grupo completo (padre y opcionalmente variaciones)."""
        # Obtener grupos disponibles
        groups = self.df[self.df['Tipo'] == 'variable']
        
        if len(groups) == 0:
            messagebox.showinfo("Info", "No hay grupos disponibles para eliminar")
            return
        
        # Diálogo de selección de grupo
        dialog = tk.Toplevel(self.root)
        dialog.title("Eliminar grupo")
        dialog.geometry("550x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Selecciona el grupo a eliminar:", 
                 font=('Segoe UI', 11, 'bold')).pack(pady=10)
        
        # Frame para lista
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        listbox = tk.Listbox(list_frame, font=('Segoe UI', 10))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        idx_map = {}
        for i, (idx, group) in enumerate(groups.iterrows()):
            # Contar variaciones
            parent_id = group['ID']
            variations = self.df[self.df['Principal'] == f'id:{parent_id}']
            var_count = len(variations)
            listbox.insert(tk.END, f"{group['SKU']} - {group['Nombre'][:35]} ({var_count} variaciones)")
            idx_map[i] = idx
        
        # Opciones
        options_frame = ttk.LabelFrame(dialog, text="Opciones", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        action_var = tk.StringVar(value="convert")
        ttk.Radiobutton(options_frame, text="Convertir variaciones a productos simples", 
                       variable=action_var, value="convert").pack(anchor='w')
        ttk.Radiobutton(options_frame, text="Eliminar todo (padre + variaciones)", 
                       variable=action_var, value="delete_all").pack(anchor='w')
        
        def on_delete():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Aviso", "Selecciona un grupo")
                return
            
            parent_idx = idx_map[sel[0]]
            parent_row = self.df.loc[parent_idx]
            parent_id = parent_row['ID']
            parent_name = parent_row['Nombre']
            
            # Encontrar variaciones
            variation_mask = self.df['Principal'] == f'id:{parent_id}'
            variation_indices = self.df[variation_mask].index.tolist()
            var_count = len(variation_indices)
            
            action = action_var.get()
            
            # Confirmar
            if action == "delete_all":
                msg = f"¿Eliminar grupo '{parent_name}' y sus {var_count} variaciones?\n\nEsta acción no se puede deshacer."
            else:
                msg = f"¿Eliminar grupo '{parent_name}'?\n\nLas {var_count} variaciones se convertirán a productos simples."
            
            if not messagebox.askyesno("Confirmar eliminación", msg):
                return
            
            if action == "delete_all":
                # Eliminar padre y variaciones
                indices_to_delete = [parent_idx] + variation_indices
                self.df = self.df.drop(indices_to_delete).reset_index(drop=True)
                self.update_status(f"Grupo '{parent_name}' eliminado con {var_count} variaciones")
            else:
                # Convertir variaciones a simples y eliminar padre
                for var_idx in variation_indices:
                    self.df.at[var_idx, 'Tipo'] = 'simple'
                    self.df.at[var_idx, 'Principal'] = ''
                    self.df.at[var_idx, 'Clase de impuesto'] = ''
                
                self.df = self.df.drop(parent_idx).reset_index(drop=True)
                self.update_status(f"Grupo '{parent_name}' eliminado. {var_count} productos convertidos a simples")
            
            self.modified = True
            self.selected_idx = None
            self.update_modified_indicator()
            self.refresh_product_list()
            self.clear_detail_panel()
            dialog.destroy()
        
        # Botones
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Eliminar grupo", command=on_delete).pack(side=tk.RIGHT, padx=5)
    
    # ===== Utilidades =====
    
    def clear_detail_panel(self):
        """Limpia el panel de detalles cuando no hay producto seleccionado."""
        # Limpiar campos básicos (StringVars)
        for field, var in self.field_vars.items():
            var.set('')
        
        # Limpiar atributos
        for i in range(6):
            self.attr_vars[i]['name'].set('')
            self.attr_vars[i]['value'].set('')
            self.attr_vars[i]['visible'].set(0)
        
        # Limpiar info del grupo
        self.group_info_label.config(text="Selecciona un producto para ver información del grupo")
        
        # Limpiar treeview de variaciones
        for item in self.var_tree.get_children():
            self.var_tree.delete(item)
    
    def update_status(self, message: str):
        """Actualiza mensaje de estado."""
        self.status_label.config(text=message)
    
    def update_modified_indicator(self):
        """Actualiza indicador de modificación."""
        if self.modified:
            self.modified_label.config(text="● Modificado", foreground='orange')
        else:
            self.modified_label.config(text="", foreground='black')
    
    def on_closing(self):
        """Maneja cierre de ventana."""
        if self.modified:
            result = messagebox.askyesnocancel(
                "Guardar cambios",
                "Hay cambios sin guardar. ¿Desea guardarlos?"
            )
            if result is None:  # Cancel
                return
            elif result:  # Yes
                self.save_file()
        
        self.root.destroy()


def main():
    """Punto de entrada principal."""
    root = tk.Tk()
    
    # Configurar DPI awareness en Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = ProductReviewerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
