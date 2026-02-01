"""
Validador de atributos extraídos del catálogo PDF vs WooCommerce/Maestro.

Permite por cada SKU:
- Aceptar: usar los atributos extraídos del PDF.
- Mantener anterior: conservar los atributos actuales del maestro/WooCommerce.
- Borrar: dejar el atributo vacío (o eliminar).

Uso:
  python validador_atributos_catalogo.py
  python validador_atributos_catalogo.py data/catalogo_mamut_2025_extracted.json data/processed/maestro_revision_*.xlsx
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import sys

try:
    import pandas as pd
except ImportError:
    pd = None


def load_extracted(json_path: str) -> dict:
    """Carga el JSON del catálogo extraído del PDF."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def load_maestro(path: str) -> pd.DataFrame | None:
    """Carga el maestro (Excel o CSV) con columnas de atributos WooCommerce."""
    if pd is None:
        return None
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8")
    return pd.read_excel(path, sheet_name="Maestro")


def get_current_attributes(row: pd.Series, attr_cols: list) -> list[dict]:
    """Extrae de una fila del maestro los atributos actuales (nombre, valor)."""
    out = []
    for name_col, val_col, _vis, _glob in attr_cols:
        name = row.get(name_col, "")
        val = row.get(val_col, "")
        if pd.isna(name):
            name = ""
        if pd.isna(val):
            val = ""
        if str(name).strip() or str(val).strip():
            out.append({"name": str(name).strip(), "value": str(val).strip()})
    return out


# Columnas WooCommerce estándar (nombre, valor, visible, global) x 6
ATTR_COLS = [
    ("Nombre del atributo 1", "Valor(es) del atributo 1", "Atributo visible 1", "Atributo global 1"),
    ("Nombre del atributo 2", "Valor(es) del atributo 2", "Atributo visible 2", "Atributo global 2"),
    ("Nombre del atributo 3", "Valor(es) del atributo 3", "Atributo visible 3", "Atributo global 3"),
    ("Nombre del atributo 4", "Valor(es) del atributo 4", "Atributo visible 4", "Atributo global 4"),
    ("Nombre del atributo 5", "Valor(es) del atributo 5", "Atributo visible 5", "Atributo global 5"),
    ("Nombre del atributo 6", "Valor(es) del atributo 6", "Atributo visible 6", "Atributo global 6"),
]


class ValidadorAtributosGUI:
    """Ventana para validar atributos: Aceptar extraídos / Mantener anterior / Borrar."""

    def __init__(self, root):
        self.root = root
        self.root.title("Validar atributos del catálogo PDF vs WooCommerce")
        self.root.geometry("1000x700")
        self.root.minsize(800, 500)

        self.extracted_data: dict = {}
        self.df_maestro: pd.DataFrame | None = None
        self.sku_list: list[str] = []
        self.current_index = 0
        self.decisions: dict[str, str] = {}  # sku -> "accept" | "keep" | "delete"
        self.merged_woo: dict[str, dict] = {}  # sku -> { Nombre attr 1: ..., Valor 1: ..., ... }

        self.setup_ui()
        self.load_initial()

    def setup_ui(self):
        """Crea menú y layout."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Abrir catálogo extraído (JSON)...", command=self.open_extracted)
        file_menu.add_command(label="Abrir maestro (Excel/CSV)...", command=self.open_maestro)
        file_menu.add_separator()
        file_menu.add_command(label="Exportar decisiones a JSON", command=self.export_decisions)
        file_menu.add_command(label="Aplicar al maestro y guardar", command=self.apply_to_maestro)

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Filtro / búsqueda
        search_f = ttk.Frame(main)
        search_f.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_f, text="SKU:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.filter_sku_list())
        ttk.Entry(search_f, textvariable=self.search_var, width=25).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Lista de SKUs
        list_f = ttk.LabelFrame(main, text="SKUs a validar", padding=5)
        list_f.pack(fill=tk.BOTH, expand=True)
        self.sku_listbox = tk.Listbox(list_f, height=12, font=("Consolas", 10))
        sb = ttk.Scrollbar(list_f)
        self.sku_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.sku_listbox.config(yscrollcommand=sb.set)
        sb.config(command=self.sku_listbox.yview)
        self.sku_listbox.bind("<<ListboxSelect>>", self.on_sku_select)

        # Detalle: extraídos vs actuales
        detail_f = ttk.LabelFrame(main, text="Atributos: Extraídos (PDF) vs Actuales (Maestro)", padding=10)
        detail_f.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.detail_text = tk.Text(detail_f, height=10, font=("Consolas", 9), wrap=tk.WORD)
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        # Botones de decisión
        btn_f = ttk.Frame(main)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="✓ Aceptar (usar extraídos)", command=lambda: self.set_decision("accept")).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_f, text="↩ Mantener anterior", command=lambda: self.set_decision("keep")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="✗ Borrar atributos", command=lambda: self.set_decision("delete")).pack(
            side=tk.LEFT, padx=5
        )
        self.decision_label = ttk.Label(btn_f, text="")
        self.decision_label.pack(side=tk.LEFT, padx=20)

        self.status_label = ttk.Label(main, text="Carga el JSON del catálogo extraído y opcionalmente el maestro.")
        self.status_label.pack(fill=tk.X)

    def load_initial(self):
        """Carga archivos si se pasaron por línea de comandos."""
        args = sys.argv[1:]
        if len(args) >= 1:
            self.load_extracted_file(args[0])
        if len(args) >= 2:
            self.load_maestro_file(args[1])

    def open_extracted(self):
        path = filedialog.askopenfilename(
            title="Catálogo extraído (JSON)",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
            initialdir="data",
        )
        if path:
            self.load_extracted_file(path)

    def load_extracted_file(self, path: str):
        try:
            self.extracted_data = load_extracted(path)
            self.sku_list = sorted(self.extracted_data.get("products", {}).keys())
            self.filter_sku_list()
            self.status_label.config(text=f"Catálogo: {path} — {len(self.sku_list)} SKUs")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_maestro(self):
        path = filedialog.askopenfilename(
            title="Maestro (Excel/CSV)",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv"), ("Todos", "*.*")],
            initialdir="data/processed",
        )
        if path:
            self.load_maestro_file(path)

    def load_maestro_file(self, path: str):
        if pd is None:
            messagebox.showerror("Error", "Se necesita pandas para cargar el maestro.")
            return
        try:
            self.df_maestro = load_maestro(path)
            self.status_label.config(
                text=self.status_label.cget("text") + f" | Maestro: {path} ({len(self.df_maestro)} filas)"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def filter_sku_list(self):
        q = self.search_var.get().strip().upper()
        if not self.sku_list:
            self.sku_listbox.delete(0, tk.END)
            return
        filtered = [s for s in self.sku_list if q in s.upper()]
        self.sku_listbox.delete(0, tk.END)
        for s in filtered:
            self.sku_listbox.insert(tk.END, s)
        if filtered and self.sku_listbox.curselection():
            pass
        elif filtered:
            self.sku_listbox.selection_set(0)
            self.sku_listbox.event_generate("<<ListboxSelect>>")

    def on_sku_select(self, event):
        sel = self.sku_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        items = self.sku_listbox.get(0, tk.END)
        if idx >= len(items):
            return
        sku = items[idx]
        self.current_index = idx
        self.show_detail(sku)

    def show_detail(self, sku: str):
        """Muestra atributos extraídos vs actuales para el SKU."""
        self.detail_text.delete("1.0", tk.END)
        products = self.extracted_data.get("products", {})
        woo_extracted = self.extracted_data.get("attributes_woocommerce", {}).get(sku, {})

        lines = [f"SKU: {sku}\n", "--- EXTRAÍDOS (PDF) ---\n"]
        for i in range(1, 7):
            name = woo_extracted.get(f"Nombre del atributo {i}", "")
            val = woo_extracted.get(f"Valor(es) del atributo {i}", "")
            if name or val:
                lines.append(f"  {name}: {val}\n")
        lines.append("\n--- ACTUALES (Maestro) ---\n")

        current = []
        if self.df_maestro is not None and "SKU" in self.df_maestro.columns:
            match = self.df_maestro[self.df_maestro["SKU"].astype(str).str.strip() == str(sku).strip()]
            if not match.empty:
                row = match.iloc[0]
                for name_col, val_col, _, _ in ATTR_COLS:
                    if name_col in row and val_col in row:
                        n, v = row.get(name_col, ""), row.get(val_col, "")
                        if pd.notna(n) or pd.notna(v):
                            current.append((str(n) if pd.notna(n) else "", str(v) if pd.notna(v) else ""))
        for n, v in current:
            lines.append(f"  {n}: {v}\n")
        if not current:
            lines.append("  (sin datos en maestro)\n")

        dec = self.decisions.get(sku, "")
        if dec == "accept":
            lines.append("\n→ Decisión: Aceptar extraídos\n")
        elif dec == "keep":
            lines.append("\n→ Decisión: Mantener anterior\n")
        elif dec == "delete":
            lines.append("\n→ Decisión: Borrar\n")

        self.detail_text.insert("1.0", "".join(lines))
        self.decision_label.config(text=f"Decisión: {self.decisions.get(sku, '—')}")

    def set_decision(self, decision: str):
        sel = self.sku_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Selecciona un SKU.")
            return
        items = self.sku_listbox.get(0, tk.END)
        sku = items[sel[0]]
        self.decisions[sku] = decision

        # Calcular merged para este SKU
        woo_extracted = self.extracted_data.get("attributes_woocommerce", {}).get(sku, {})
        if decision == "accept":
            self.merged_woo[sku] = dict(woo_extracted)
        elif decision == "keep" and self.df_maestro is not None and "SKU" in self.df_maestro.columns:
            match = self.df_maestro[self.df_maestro["SKU"].astype(str).str.strip() == str(sku).strip()]
            if not match.empty:
                row = match.iloc[0]
                merged = {}
                for i in range(1, 7):
                    name_key = f"Nombre del atributo {i}"
                    val_key = f"Valor(es) del atributo {i}"
                    merged[name_key] = str(row.get(name_key, "")) if pd.notna(row.get(name_key)) else ""
                    merged[val_key] = str(row.get(val_key, "")) if pd.notna(row.get(val_key)) else ""
                self.merged_woo[sku] = merged
            else:
                self.merged_woo[sku] = {k: "" for k in woo_extracted}
        else:  # delete
            self.merged_woo[sku] = {k: "" for k in woo_extracted}

        self.show_detail(sku)
        self.status_label.config(text=f"Decisión para {sku}: {decision}")

    def export_decisions(self):
        """Guarda decisiones y atributos mergeados en JSON."""
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir="data",
            initialfile="atributos_validados.json",
        )
        if not path:
            return
        out = {
            "decisions": self.decisions,
            "merged_attributes_woocommerce": self.merged_woo,
            "catalog_name": self.extracted_data.get("catalog_name", ""),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Guardado", f"Guardado en {path}")

    def apply_to_maestro(self):
        """Actualiza el maestro con los atributos mergeados y guarda."""
        if self.df_maestro is None:
            messagebox.showwarning("Aviso", "Carga primero un maestro (Excel/CSV).")
            return
        if not self.merged_woo:
            messagebox.showwarning("Aviso", "No hay decisiones aplicadas. Elige Aceptar/Mantener/Borrar para al menos un SKU.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
            initialdir="data/processed",
        )
        if not path:
            return
        try:
            df = self.df_maestro.copy()
            for name_col, val_col, vis_col, glob_col in ATTR_COLS:
                if name_col not in df.columns:
                    df[name_col] = ""
                if val_col not in df.columns:
                    df[val_col] = ""
                if vis_col not in df.columns:
                    df[vis_col] = 1
                if glob_col not in df.columns:
                    df[glob_col] = 0
            for sku, woo in self.merged_woo.items():
                match = df["SKU"].astype(str).str.strip() == str(sku).strip()
                if not match.any():
                    continue
                idx = match.idxmax()
                for name_col, val_col, _vis, _glob in ATTR_COLS:
                    if name_col in df.columns and val_col in df.columns:
                        df.at[idx, name_col] = woo.get(name_col, "")
                        df.at[idx, val_col] = woo.get(val_col, "")
            if path.lower().endswith(".csv"):
                df.to_csv(path, index=False, encoding="utf-8")
            else:
                df.to_excel(path, sheet_name="Maestro", index=False)
            messagebox.showinfo("Guardado", f"Maestro actualizado guardado en {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def main():
    root = tk.Tk()
    ValidadorAtributosGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
