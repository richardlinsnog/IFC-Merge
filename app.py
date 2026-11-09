"""IFC Merger — unifica múltiplos arquivos IFC em um único arquivo."""

import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

import ifcopenshell
from ifcpatch.recipes import MergeProjects, Migrate

# Preferimos sempre "subir" de schema (upgrade), nunca descer: downgrade
# (ex.: IFC4 -> IFC2X3) é lossy e falha em classes só existentes no mais novo.
_SCHEMA_RANK = {"IFC2X3": 0, "IFC4": 1, "IFC4X3": 2}


class IFCMergerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IFC Merger")
        self.root.geometry("620x640")
        self.root.minsize(560, 520)

        self.files: list[str] = []
        self.export_dir: str = ""
        self._merging = False
        self._cancel = False
        self._queue: queue.Queue = queue.Queue()
        self._remove_buttons: list[tk.Button] = []

        # 1) Seleção de modelos
        self.btn_select = tk.Button(root, text="Select models", command=self.select_models)
        self.btn_select.pack(pady=(10, 2), padx=12, fill="x")

        self.lbl_count = tk.Label(root, text="0 modelo(s) selecionado(s)")
        self.lbl_count.pack(pady=2)

        # Lista rolável de modelos (cada item com "X" para remover)
        self.list_container = tk.Frame(root)
        self.list_container.pack(fill="both", expand=True, padx=12, pady=(2, 4))
        self._build_list()

        # 2) Pasta de exportação
        self.btn_export = tk.Button(root, text="Export path", command=self.select_export)
        self.btn_export.pack(pady=(4, 2), padx=12, fill="x")

        self.export_var = tk.StringVar(value="")
        self.entry_export = tk.Entry(root, textvariable=self.export_var, state="readonly")
        self.entry_export.pack(pady=2, padx=12, fill="x")

        # 3) Merge
        self.btn_merge = tk.Button(root, text="Merge IFC files", command=self.start_merge)
        self.btn_merge.pack(pady=(6, 2), padx=12, fill="x")

        self.btn_cancel = tk.Button(root, text="Cancelar", command=self.cancel_merge, state="disabled")
        self.btn_cancel.pack(pady=2, padx=12, fill="x")

        # Log de progresso
        self.log = tk.Text(root, height=8, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self._append_log("Pronto.")

    # ------------------------------------------------------------------ #
    # Interface
    # ------------------------------------------------------------------ #
    def _build_list(self) -> None:
        self.list_canvas = tk.Canvas(self.list_container, highlightthickness=0)
        self.list_scroll = ttk.Scrollbar(
            self.list_container, orient="vertical", command=self.list_canvas.yview
        )
        self.list_inner = tk.Frame(self.list_canvas)
        self.list_inner.bind(
            "<Configure>",
            lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")),
        )
        self.list_window = self.list_canvas.create_window((0, 0), window=self.list_inner, anchor="nw")
        self.list_canvas.bind(
            "<Configure>",
            lambda e: self.list_canvas.itemconfigure(self.list_window, width=e.width),
        )
        self.list_canvas.configure(yscrollcommand=self.list_scroll.set)
        self.list_scroll.pack(side="right", fill="y")
        self.list_canvas.pack(side="left", fill="both", expand=True)

        for w in (self.list_canvas, self.list_inner):
            w.bind("<MouseWheel>", self._on_list_wheel)

        self._render_list()

    def _on_list_wheel(self, event) -> None:
        self.list_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _render_list(self) -> None:
        for child in self.list_inner.winfo_children():
            child.destroy()
        self._remove_buttons = []

        if not self.files:
            tk.Label(
                self.list_inner, text="Nenhum modelo adicionado.", fg="grey", anchor="w"
            ).pack(fill="x", padx=4, pady=4)
            return

        for i, path in enumerate(self.files):
            row = tk.Frame(self.list_inner)
            row.pack(fill="x", pady=1)
            btn = tk.Button(
                row,
                text="✕",
                width=2,
                relief="flat",
                fg="red",
                command=lambda idx=i: self.remove_model(idx),
            )
            btn.pack(side="left")
            self._remove_buttons.append(btn)
            tk.Label(row, text=path, anchor="w").pack(side="left", fill="x", expand=True)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        self._merging = busy
        state = "disabled" if busy else "normal"
        self.btn_select.configure(state=state)
        self.btn_export.configure(state=state)
        self.btn_merge.configure(state=state)
        self.btn_cancel.configure(state="normal" if busy else "disabled")
        for btn in self._remove_buttons:
            btn.configure(state=state)

    # ------------------------------------------------------------------ #
    # Ações do usuário
    # ------------------------------------------------------------------ #
    def select_models(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecionar modelos IFC",
            filetypes=[
                ("IFC files", "*.ifc *.ifczip *.ifcxml"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        existing = set(self.files)
        added = 0
        for p in paths:
            if p not in existing:
                self.files.append(p)
                existing.add(p)
                added += 1
        if added:
            self._render_list()
            self.lbl_count.config(text=f"{len(self.files)} modelo(s) selecionado(s)")

    def remove_model(self, index: int) -> None:
        if self._merging or not (0 <= index < len(self.files)):
            return
        del self.files[index]
        self._render_list()
        self.lbl_count.config(text=f"{len(self.files)} modelo(s) selecionado(s)")

    def select_export(self) -> None:
        path = filedialog.askdirectory(title="Selecionar pasta de exportação")
        if not path:
            return
        self.export_dir = path
        self.export_var.set(path)

    def cancel_merge(self) -> None:
        self._cancel = True
        self._append_log("Cancelamento solicitado...")

    # ------------------------------------------------------------------ #
    # Merge
    # ------------------------------------------------------------------ #
    def start_merge(self) -> None:
        if len(self.files) < 2:
            messagebox.showerror("Erro", "Selecione pelo menos 2 modelos IFC.")
            return
        if not self.export_dir:
            messagebox.showerror("Erro", "Selecione uma pasta de exportação.")
            return
        for path in self.files:
            if not os.path.exists(path):
                messagebox.showerror("Erro", f"Arquivo não encontrado:\n{path}")
                return
        if not os.path.isdir(self.export_dir):
            messagebox.showerror("Erro", f"Pasta não encontrada:\n{self.export_dir}")
            return

        out_path = os.path.join(self.export_dir, "merged.ifc")
        files = list(self.files)
        self._cancel = False
        self._set_busy(True)
        threading.Thread(target=self._merge_worker, args=(files, out_path), daemon=True).start()
        self.root.after(100, self._poll_queue)

    def _merge_worker(self, files: list[str], out_path: str) -> None:
        try:
            self._queue.put(("log", f"Abrindo {len(files)} arquivos..."))
            models = []
            for path in files:
                if self._cancel:
                    self._queue.put(("cancelled", None))
                    return
                self._queue.put(("log", f"Abrindo {os.path.basename(path)}..."))
                models.append(ifcopenshell.open(path))

            target_schema = max(
                (m.schema for m in models), key=lambda s: _SCHEMA_RANK.get(s, 0)
            )
            self._queue.put(("log", f"Schema de destino: {target_schema}"))

            def prepare(model, path):
                if self._cancel:
                    raise _Cancelled()
                if model.schema != target_schema:
                    self._queue.put(
                        ("log", f"Convertendo {os.path.basename(path)} ({model.schema} -> {target_schema})...")
                    )
                    migrator = Migrate.Patcher(file=model, schema=target_schema)
                    migrator.patch()
                    model = migrator.get_output()
                return model

            base = prepare(models[0], files[0])
            others = [prepare(m, p) for m, p in zip(models[1:], files[1:])]

            self._queue.put(("log", f"Mesclando {len(models)} modelos..."))
            patcher = MergeProjects.Patcher(file=base, filepaths=[])
            for i, other in enumerate(others, 1):
                if self._cancel:
                    self._queue.put(("cancelled", None))
                    return
                self._queue.put(
                    ("log", f"Mesclando modelo {i}/{len(others)} ({os.path.basename(files[i])})...")
                )
                patcher.merge(other)

            self._queue.put(("log", "Salvando merged.ifc..."))
            merged = patcher.get_output()
            merged.write(out_path)
            self._queue.put(("log", f"Arquivo salvo em: {out_path}"))
            self._queue.put(("success", out_path))
        except _Cancelled:
            self._queue.put(("cancelled", None))
        except Exception as exc:  # noqa: BLE001 — mensagem é exibida ao usuário
            self._queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "success":
                    self._set_busy(False)
                    self._append_log("Concluído.")
                    messagebox.showinfo("Sucesso", f"Merge concluído!\n\nArquivo salvo em:\n{payload}")
                    return
                elif kind == "error":
                    self._set_busy(False)
                    self._append_log("Erro.")
                    messagebox.showerror("Erro", f"Falha ao executar o merge:\n{payload}")
                    return
                elif kind == "cancelled":
                    self._set_busy(False)
                    self._append_log("Merge cancelado.")
                    messagebox.showinfo("Cancelado", "O merge foi cancelado.")
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


class _Cancelled(Exception):
    pass


def main() -> None:
    root = tk.Tk()
    IFCMergerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
