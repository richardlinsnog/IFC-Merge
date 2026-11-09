"""IFC Merger — unifica múltiplos arquivos IFC em um único arquivo."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import ifcopenshell
from ifcpatch.recipes import MergeProjects


class IFCMergerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IFC Merger")
        self.root.resizable(False, False)

        self.files: list[str] = []
        self.export_dir: str = ""

        # Controles na ordem vertical exigida pela especificação.
        self.btn_select = tk.Button(
            root, text="Select models", command=self.select_models
        )
        self.btn_select.pack(pady=5, padx=20, fill="x")

        self.lbl_count = tk.Label(root, text="0 modelo(s) selecionado(s)")
        self.lbl_count.pack(pady=5)

        self.btn_export = tk.Button(
            root, text="Export path", command=self.select_export
        )
        self.btn_export.pack(pady=5, padx=20, fill="x")

        self.lbl_export = tk.Label(root, text="Nenhuma pasta selecionada")
        self.lbl_export.pack(pady=5)

        self.btn_merge = tk.Button(
            root, text="Merge IFC files", command=self.merge
        )
        self.btn_merge.pack(pady=10, padx=20, fill="x")

    def select_models(self) -> None:
        """Abre diálogo de seleção múltipla e preserva a ordem de seleção."""
        paths = filedialog.askopenfilenames(
            title="Selecionar modelos IFC",
            filetypes=[
                ("IFC files", "*.ifc *.ifczip *.ifcxml"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        # askopenfilenames já devolve na ordem de seleção; mantemos como está.
        self.files = list(paths)
        self.lbl_count.config(text=f"{len(self.files)} modelo(s) selecionado(s)")

    def select_export(self) -> None:
        """Abre diálogo de seleção de pasta de exportação."""
        path = filedialog.askdirectory(title="Selecionar pasta de exportação")
        if not path:
            return
        self.export_dir = path
        self.lbl_export.config(text=path)

    def merge(self) -> None:
        """Executa o merge via ifcpatch (recipe MergeProjects)."""
        if len(self.files) < 2:
            messagebox.showerror("Erro", "Selecione pelo menos 2 modelos IFC.")
            return

        if not self.export_dir:
            messagebox.showerror("Erro", "Selecione uma pasta de exportação.")
            return

        # Valida que os caminhos selecionados ainda existem antes de abrir.
        for path in self.files:
            if not os.path.exists(path):
                messagebox.showerror("Erro", f"Arquivo não encontrado:\n{path}")
                return
        if not os.path.isdir(self.export_dir):
            messagebox.showerror("Erro", f"Pasta não encontrada:\n{self.export_dir}")
            return

        out_path = os.path.join(self.export_dir, "merged.ifc")

        try:
            first = ifcopenshell.open(self.files[0])
            # Chamamos o Patcher diretamente: ifcpatch.execute desempacota
            # "arguments" de forma quebrada para MergeProjects com 3+ arquivos.
            patcher = MergeProjects.Patcher(file=first, filepaths=self.files[1:])
            patcher.patch()
            merged = patcher.get_output()
            merged.write(out_path)
        except Exception as exc:  # noqa: BLE001 — mensagem é exibida ao usuário
            messagebox.showerror("Erro", f"Falha ao executar o merge:\n{exc}")
            return

        messagebox.showinfo(
            "Sucesso",
            f"Merge concluído!\n\nArquivo salvo em:\n{out_path}",
        )


def main() -> None:
    root = tk.Tk()
    IFCMergerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
