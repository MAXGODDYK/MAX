from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import database as db
from google_sheets_sync import GoogleSheetsSynchronizer, SyncResult


def money(value: float | None) -> str:
    return "неизвестно" if value is None else f"{value:.2f} грн"


def number_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def initialize_local_database(sync: GoogleSheetsSynchronizer, db_path=db.DB_PATH) -> bool:
    first_run_remote_cache = not db_path.exists() and sync.enabled
    if first_run_remote_cache:
        db.init_remote_cache_db(db_path)
    else:
        db.init_db(db_path)
    return first_run_remote_cache


class IngredientTab(ttk.Frame):
    def __init__(self, master: ttk.Notebook, table_key: str, app: "TobaccoMixApp") -> None:
        super().__init__(master, padding=10)
        self.table_key = table_key
        self.meta = db.ITEM_TABLES[table_key]
        self.app = app
        self.search_var = tk.StringVar()
        self.filter_vars: dict[str, tk.StringVar] = {}
        self.entries: dict[str, tk.Widget] = {}
        self.classification_var = tk.StringVar()
        self.current_id: int | None = None
        self.current_packaging_id: int | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Поиск").pack(side="left")
        search = ttk.Entry(top, textvariable=self.search_var, width=28)
        search.pack(side="left", padx=(6, 10))
        search.bind("<KeyRelease>", lambda _event: self.refresh())

        for field, label in self.meta["filter_fields"]:
            ttk.Label(top, text=label).pack(side="left", padx=(6, 2))
            var = tk.StringVar()
            combo = ttk.Combobox(top, textvariable=var, width=18, state="readonly")
            combo.pack(side="left")
            combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
            self.filter_vars[field] = var

        ttk.Button(top, text="Сброс", command=self.reset_filters).pack(side="left", padx=6)

        columns = ("price_uah", "package_amount_g", "seller", "extra")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", height=11)
        self.tree.heading("#0", text="Название / фасовка")
        self.tree.column("#0", width=310, anchor="w")
        headers = {
            "price_uah": "Цена",
            "package_amount_g": "Упаковка, г",
            "seller": "Продавец",
            "extra": "Классификация/тип",
        }
        widths = {"price_uah": 80, "package_amount_g": 100, "seller": 150, "extra": 240}
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill="both", expand=True, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.LabelFrame(self, text="Карточка ингредиента", padding=10)
        form.pack(fill="x")
        for index, (field, label, field_type) in enumerate(db.form_fields_for(self.table_key)):
            row = index // 3
            col = (index % 3) * 2
            ttk.Label(form, text=label).grid(row=row, column=col, sticky="w", padx=(0, 4), pady=3)
            entry: tk.Widget
            if self.table_key == "tobacco" and field == "classification":
                entry = ttk.Combobox(
                    form,
                    textvariable=self.classification_var,
                    width=22,
                    state="readonly",
                    values=["", *db.tobacco_classification_names()],
                )
                entry.grid(row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=3)
            elif self.table_key == "tobacco" and field == "strength":
                combo = ttk.Combobox(form, width=22, state="readonly", values=db.tobacco_strength_names())
                combo.grid(row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=3)
                entry = combo
            elif self.table_key == "tobacco" and field == "cut":
                combo = ttk.Combobox(form, width=22, state="readonly", values=db.tobacco_cut_names())
                combo.grid(row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=3)
                entry = combo
            elif field == "notes":
                entry = ttk.Entry(form, width=34)
                entry.grid(row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=3)
            else:
                entry = ttk.Entry(form, width=24)
                entry.grid(row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=3)
            self.entries[field] = entry
        for col in range(0, 6, 2):
            form.columnconfigure(col + 1, weight=1)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Новый", command=self.clear_form).pack(side="left")
        ttk.Button(buttons, text="Сохранить", command=self.save).pack(side="left", padx=6)
        ttk.Button(buttons, text="Удалить", command=self.delete).pack(side="left")

        packaging_buttons = ttk.LabelFrame(self, text="Фасовки", padding=8)
        packaging_buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(packaging_buttons, text="Добавить фасовку", command=self.add_packaging).pack(side="left")
        ttk.Button(packaging_buttons, text="Изменить фасовку", command=self.edit_packaging).pack(side="left", padx=6)
        ttk.Button(packaging_buttons, text="Удалить фасовку", command=self.delete_packaging).pack(side="left")
        ttk.Button(packaging_buttons, text="Сделать основной", command=self.make_default_packaging).pack(side="left", padx=6)

    @staticmethod
    def item_iid(item_id: object) -> str:
        return f"item:{item_id}"

    @staticmethod
    def packaging_iid(packaging_id: object) -> str:
        return f"packaging:{packaging_id}"

    @staticmethod
    def parse_iid(iid: str) -> tuple[str, int] | tuple[None, None]:
        if ":" not in iid:
            return None, None
        kind, raw_id = iid.split(":", 1)
        try:
            return kind, int(raw_id)
        except ValueError:
            return None, None

    def reset_filters(self) -> None:
        self.search_var.set("")
        for var in self.filter_vars.values():
            var.set("")
        self.refresh()

    def refresh_filter_options(self) -> None:
        for field, var in self.filter_vars.items():
            combo = None
            for child in self.winfo_children():
                combo = combo
            values = ["", *db.distinct_values(self.table_key, field)]
            # Combobox widgets are kept in creation order; update via named tkinter children.
            for widget in self.winfo_children()[0].winfo_children():
                if isinstance(widget, ttk.Combobox) and widget.cget("textvariable") == str(var):
                    widget["values"] = values
                    break
        if self.table_key == "tobacco" and "strength" in self.entries:
            strength_widget = self.entries["strength"]
            if isinstance(strength_widget, ttk.Combobox):
                strength_widget["values"] = ["", *db.tobacco_strength_names()]
        if self.table_key == "tobacco" and "cut" in self.entries:
            cut_widget = self.entries["cut"]
            if isinstance(cut_widget, ttk.Combobox):
                cut_widget["values"] = ["", *db.tobacco_cut_names()]
        if self.table_key == "tobacco" and "classification" in self.entries:
            classification_widget = self.entries["classification"]
            if isinstance(classification_widget, ttk.Combobox):
                classification_widget["values"] = ["", *db.tobacco_classification_names()]

    def refresh(self) -> None:
        self.refresh_filter_options()
        filters = {field: var.get() for field, var in self.filter_vars.items()}
        rows = db.list_items(self.table_key, self.search_var.get(), filters)
        self.tree.delete(*self.tree.get_children())
        extra_fields = [field for field, _label, _type in self.meta["extra_fields"]]
        for row in rows:
            extra = " / ".join(str(row[field]) for field in extra_fields if row[field])
            packagings = db.list_packagings(self.table_key, int(row["id"]))
            if packagings:
                extra = f"{extra} | Фасовок: {len(packagings)}" if extra else f"Фасовок: {len(packagings)}"
            item_iid = self.item_iid(row["id"])
            self.tree.insert(
                "",
                "end",
                iid=item_iid,
                text=row["name"],
                values=(
                    number_text(row["price_uah"]),
                    number_text(row["package_amount_g"]),
                    row["seller"] or "",
                    extra,
                ),
            )
            for packaging in packagings:
                suffix = " [основная]" if packaging["is_default"] else ""
                self.tree.insert(
                    item_iid,
                    "end",
                    iid=self.packaging_iid(packaging["id"]),
                    text=f"Фасовка: {db.packaging_label(packaging)}{suffix}",
                    values=(
                        number_text(packaging["price_uah"]),
                        number_text(packaging["package_amount_g"]),
                        "",
                        packaging["url"] or packaging["notes"] or "",
                    ),
                )
        self.app.refresh_calculator_sources()

    def on_select(self, _event: object | None = None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        row_kind, row_id = self.parse_iid(selection[0])
        if row_kind == "packaging":
            packaging = db.get_item_packaging(row_id)
            if not packaging:
                return
            self.current_packaging_id = row_id
            self.current_id = int(packaging["item_id"])
        elif row_kind == "item":
            self.current_id = row_id
            self.current_packaging_id = None
        else:
            return
        row = db.get_item(self.table_key, self.current_id)
        if not row:
            return
        for field, _label, _type in db.form_fields_for(self.table_key):
            entry = self.entries[field]
            if self.table_key == "tobacco" and field == "classification":
                names = db.get_tobacco_classification_names(self.current_id)
                self.classification_var.set(names[0] if names else number_text(row[field]))
                continue
            if self.table_key == "tobacco" and field == "strength" and isinstance(entry, ttk.Combobox):
                entry.set(number_text(row[field]))
                continue
            if self.table_key == "tobacco" and field == "cut" and isinstance(entry, ttk.Combobox):
                entry.set(number_text(row[field]))
                continue
            if isinstance(entry, ttk.Combobox):
                entry.set(number_text(row[field]))
                continue
            entry.delete(0, tk.END)
            entry.insert(0, number_text(row[field]))

    def form_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for field, entry in self.entries.items():
            values[field] = entry.get().strip()
        return values

    def clear_form(self) -> None:
        self.current_id = None
        self.current_packaging_id = None
        self.tree.selection_remove(self.tree.selection())
        self.classification_var.set("")
        for field, entry in self.entries.items():
            if self.table_key == "tobacco" and field == "classification":
                continue
            if isinstance(entry, ttk.Combobox):
                entry.set("")
                continue
            entry.delete(0, tk.END)

    def save(self) -> None:
        try:
            saved_id = db.save_item(self.table_key, self.form_values(), self.current_id)
        except Exception as exc:
            messagebox.showerror("Не удалось сохранить", str(exc))
            return
        self.current_id = saved_id
        self.current_packaging_id = None
        self.refresh()
        self.tree.selection_set(self.item_iid(saved_id))
        self.app.after_data_changed()
        messagebox.showinfo("Сохранено", "Карточка ингредиента сохранена.")

    def delete(self) -> None:
        if self.current_id is None:
            messagebox.showwarning("Не выбрано", "Выберите ингредиент для удаления.")
            return
        if not messagebox.askyesno("Удалить", "Удалить выбранную карточку?"):
            return
        db.delete_item(self.table_key, self.current_id)
        self.clear_form()
        self.refresh()
        self.app.after_data_changed()

    def selected_packaging_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            return self.current_packaging_id
        row_kind, row_id = self.parse_iid(selection[0])
        return row_id if row_kind == "packaging" else self.current_packaging_id

    def add_packaging(self) -> None:
        if self.current_id is None:
            messagebox.showwarning("Не выбрано", "Сначала выберите или сохраните товар.")
            return
        self.open_packaging_dialog()

    def edit_packaging(self) -> None:
        packaging_id = self.selected_packaging_id()
        if packaging_id is None:
            messagebox.showwarning("Не выбрано", "Выберите строку фасовки в списке.")
            return
        packaging = db.get_item_packaging(packaging_id)
        if not packaging:
            messagebox.showerror("Ошибка", "Фасовка не найдена.")
            return
        self.open_packaging_dialog(packaging)

    def delete_packaging(self) -> None:
        packaging_id = self.selected_packaging_id()
        if packaging_id is None:
            messagebox.showwarning("Не выбрано", "Выберите строку фасовки в списке.")
            return
        if not messagebox.askyesno("Удалить фасовку", "Удалить выбранную фасовку?"):
            return
        db.delete_item_packaging(packaging_id)
        self.current_packaging_id = None
        self.refresh()
        if self.current_id is not None:
            self.tree.selection_set(self.item_iid(self.current_id))
        self.app.after_data_changed()

    def make_default_packaging(self) -> None:
        packaging_id = self.selected_packaging_id()
        if packaging_id is None:
            messagebox.showwarning("Не выбрано", "Выберите строку фасовки в списке.")
            return
        db.set_default_packaging(packaging_id)
        self.current_packaging_id = packaging_id
        self.refresh()
        self.tree.selection_set(self.packaging_iid(packaging_id))
        self.app.after_data_changed()

    def open_packaging_dialog(self, packaging=None) -> None:
        if self.current_id is None:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Фасовка")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.columnconfigure(1, weight=1)

        values = {
            "label": number_text(packaging["label"]) if packaging else "",
            "package_amount_g": number_text(packaging["package_amount_g"]) if packaging else "",
            "price_uah": number_text(packaging["price_uah"]) if packaging else "",
            "url": number_text(packaging["url"]) if packaging else "",
            "notes": number_text(packaging["notes"]) if packaging else "",
        }
        variables = {field: tk.StringVar(value=value) for field, value in values.items()}
        rows = [
            ("label", "Название фасовки"),
            ("package_amount_g", "Вес/объём, г"),
            ("price_uah", "Цена, грн"),
            ("url", "Ссылка"),
            ("notes", "Заметки"),
        ]
        for row_index, (field, label) in enumerate(rows):
            ttk.Label(dialog, text=label).grid(row=row_index, column=0, sticky="w", padx=10, pady=4)
            ttk.Entry(dialog, textvariable=variables[field], width=48).grid(
                row=row_index,
                column=1,
                sticky="ew",
                padx=(0, 10),
                pady=4,
            )

        buttons = ttk.Frame(dialog)
        buttons.grid(row=len(rows), column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        def save_packaging() -> None:
            data = {field: var.get().strip() for field, var in variables.items()}
            try:
                saved_id = db.save_item_packaging(
                    self.table_key,
                    self.current_id,
                    data,
                    packaging_id=int(packaging["id"]) if packaging else None,
                )
            except Exception as exc:
                messagebox.showerror("Не удалось сохранить фасовку", str(exc), parent=dialog)
                return
            self.current_packaging_id = saved_id
            dialog.destroy()
            self.refresh()
            self.tree.selection_set(self.packaging_iid(saved_id))
            self.app.after_data_changed()

        ttk.Button(buttons, text="Сохранить", command=save_packaging).pack(side="left")
        ttk.Button(buttons, text="Отмена", command=dialog.destroy).pack(side="right")

    def choose_classifications(self) -> None:
        if self.table_key != "tobacco":
            return
        rows = db.list_tobacco_classifications()
        dialog = tk.Toplevel(self)
        dialog.title("Выбор классификации")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.geometry("360x420")
        ttk.Label(dialog, text="Выбери одну классификацию").pack(anchor="w", padx=10, pady=(10, 4))
        listbox = tk.Listbox(dialog, selectmode=tk.SINGLE, height=16)
        listbox.pack(fill="both", expand=True, padx=10, pady=4)
        names = [row["name"] for row in rows]
        for name in names:
            listbox.insert(tk.END, name)
            if name == self.classification_var.get():
                listbox.selection_set(tk.END)

        buttons = ttk.Frame(dialog)
        buttons.pack(fill="x", padx=10, pady=10)

        def apply_selection() -> None:
            selection = listbox.curselection()
            self.classification_var.set(names[selection[0]] if selection else "")
            dialog.destroy()

        def clear_selection() -> None:
            self.classification_var.set("")
            dialog.destroy()

        ttk.Button(buttons, text="Применить", command=apply_selection).pack(side="left")
        ttk.Button(buttons, text="Очистить", command=clear_selection).pack(side="left", padx=6)
        ttk.Button(buttons, text="Отмена", command=dialog.destroy).pack(side="right")


class RecipesTab(ttk.Frame):
    def __init__(self, master: ttk.Notebook, app: "TobaccoMixApp") -> None:
        super().__init__(master, padding=10)
        self.app = app
        self.current_id: int | None = None
        self.fields: dict[str, tk.Widget] = {}
        self.kind_label_to_key = {label: key for key, label in db.RECIPE_KIND_LABELS.items()}
        self.tobacco_classification_var = tk.StringVar()
        self.tobacco_strength_var = tk.StringVar()
        self.tobacco_cut_var = tk.StringVar()
        self.tobacco_cut_size_mm_var = tk.StringVar()
        self._build()
        self.refresh()

    def _build(self) -> None:
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(left, text="Рецепты").pack(anchor="w")
        self.recipe_list = tk.Listbox(left, width=30, height=20)
        self.recipe_list.pack(fill="y", expand=False, pady=(4, 8))
        self.recipe_list.bind("<<ListboxSelect>>", self.on_select)
        ttk.Button(left, text="Новый рецепт", command=self.clear_form).pack(fill="x")
        ttk.Button(left, text="Удалить рецепт", command=self.delete).pack(fill="x", pady=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)
        form = ttk.LabelFrame(right, text="Описание", padding=10)
        form.pack(fill="x")
        meta_fields = [
            ("name", "Название"),
            ("description", "Описание"),
            ("strength_level", "Крепость"),
            ("smoke_level", "Дымность"),
            ("heat_resistance", "Жаростойкость"),
            ("notes", "Заметки"),
        ]
        for index, (field, label) in enumerate(meta_fields):
            ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", pady=3)
            entry = ttk.Entry(form, width=70)
            entry.grid(row=index, column=1, sticky="ew", padx=(8, 0), pady=3)
            self.fields[field] = entry
        form.columnconfigure(1, weight=1)

        items_frame = ttk.LabelFrame(right, text="Состав, %", padding=10)
        items_frame.pack(fill="both", expand=True, pady=8)
        columns = ("kind", "label", "tobacco_classification", "tobacco_strength", "tobacco_cut", "tobacco_cut_size_mm", "percent")
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show="headings", height=8)
        for col, title, width in [
            ("kind", "Тип", 160),
            ("label", "Название строки", 220),
            ("tobacco_classification", "Вид", 130),
            ("tobacco_strength", "Крепость", 100),
            ("tobacco_cut", "Нарезка", 130),
            ("tobacco_cut_size_mm", "мм", 70),
            ("percent", "%", 80),
        ]:
            self.items_tree.heading(col, text=title)
            self.items_tree.column(col, width=width, anchor="w")
        self.items_tree.pack(fill="both", expand=True)
        self.items_tree.bind("<<TreeviewSelect>>", self.on_item_select)

        editor = ttk.Frame(items_frame)
        editor.pack(fill="x", pady=(8, 0))
        self.kind_var = tk.StringVar(value=db.RECIPE_KIND_LABELS["tobacco"])
        self.label_var = tk.StringVar(value="Табак")
        self.percent_var = tk.StringVar()
        ttk.Label(editor, text="Тип").pack(side="left")
        self.kind_combo = ttk.Combobox(
            editor,
            textvariable=self.kind_var,
            state="readonly",
            width=20,
            values=list(db.RECIPE_KIND_LABELS.values()),
        )
        self.kind_combo.pack(side="left", padx=(4, 8))
        self.kind_combo.bind("<<ComboboxSelected>>", self.on_kind_change)
        ttk.Label(editor, text="Строка").pack(side="left")
        ttk.Entry(editor, textvariable=self.label_var, width=24).pack(side="left", padx=(4, 8))
        ttk.Label(editor, text="%").pack(side="left")
        ttk.Entry(editor, textvariable=self.percent_var, width=8).pack(side="left", padx=(4, 8))
        ttk.Button(editor, text="Добавить/обновить строку", command=self.upsert_item).pack(side="left")
        ttk.Button(editor, text="Удалить строку", command=self.remove_item).pack(side="left", padx=6)

        self.tobacco_editor = ttk.Frame(items_frame)
        self.tobacco_editor.pack(fill="x", pady=(6, 0))
        ttk.Label(self.tobacco_editor, text="Вид").pack(side="left")
        self.tobacco_classification_combo = ttk.Combobox(
            self.tobacco_editor,
            textvariable=self.tobacco_classification_var,
            state="readonly",
            width=18,
            values=["", *db.tobacco_classification_names()],
        )
        self.tobacco_classification_combo.pack(side="left", padx=(4, 8))
        self.tobacco_classification_combo.bind("<<ComboboxSelected>>", self.on_tobacco_filter_change)
        ttk.Label(self.tobacco_editor, text="Крепость").pack(side="left")
        self.tobacco_strength_combo = ttk.Combobox(
            self.tobacco_editor,
            textvariable=self.tobacco_strength_var,
            state="readonly",
            width=14,
            values=["", *db.tobacco_strength_names()],
        )
        self.tobacco_strength_combo.pack(side="left", padx=(4, 8))
        ttk.Label(self.tobacco_editor, text="Нарезка").pack(side="left")
        self.tobacco_cut_combo = ttk.Combobox(
            self.tobacco_editor,
            textvariable=self.tobacco_cut_var,
            state="readonly",
            width=16,
            values=["", *db.tobacco_cut_names()],
        )
        self.tobacco_cut_combo.pack(side="left", padx=(4, 8))
        ttk.Label(self.tobacco_editor, text="мм").pack(side="left")
        self.tobacco_cut_size_entry = ttk.Entry(self.tobacco_editor, textvariable=self.tobacco_cut_size_mm_var, width=10)
        self.tobacco_cut_size_entry.pack(side="left", padx=(4, 0))

        bottom = ttk.Frame(right)
        bottom.pack(fill="x")
        self.total_label = ttk.Label(bottom, text="Сумма: 0%")
        self.total_label.pack(side="left")
        ttk.Button(bottom, text="Сохранить рецепт", command=self.save).pack(side="right")
        self.update_tobacco_filter_state()

    def selected_kind(self) -> str:
        return self.kind_label_to_key.get(self.kind_var.get(), self.kind_var.get())

    def on_kind_change(self, _event: object | None = None) -> None:
        kind = self.selected_kind()
        self.label_var.set(db.RECIPE_KIND_LABELS.get(kind, kind))
        self.update_tobacco_filter_state()

    def on_tobacco_filter_change(self, _event: object | None = None) -> None:
        if self.selected_kind() == "tobacco" and not self.label_var.get().strip():
            self.label_var.set(self.tobacco_classification_var.get().strip() or db.RECIPE_KIND_LABELS["tobacco"])

    def update_tobacco_filter_state(self) -> None:
        state = "readonly" if self.selected_kind() == "tobacco" else "disabled"
        entry_state = "normal" if self.selected_kind() == "tobacco" else "disabled"
        for combo in [self.tobacco_classification_combo, self.tobacco_strength_combo, self.tobacco_cut_combo]:
            combo.configure(state=state)
        self.tobacco_cut_size_entry.configure(state=entry_state)

    def refresh_reference_options(self) -> None:
        self.tobacco_classification_combo["values"] = ["", *db.tobacco_classification_names()]
        self.tobacco_strength_combo["values"] = ["", *db.tobacco_strength_names()]
        self.tobacco_cut_combo["values"] = ["", *db.tobacco_cut_names()]

    def refresh(self) -> None:
        self.refresh_reference_options()
        self.recipes = db.list_recipes()
        self.recipe_list.delete(0, tk.END)
        for recipe in self.recipes:
            self.recipe_list.insert(tk.END, recipe["name"])
        self.app.refresh_recipe_choices()

    def on_select(self, _event: object | None = None) -> None:
        selection = self.recipe_list.curselection()
        if not selection:
            return
        recipe = self.recipes[selection[0]]
        self.current_id = recipe["id"]
        for field, entry in self.fields.items():
            entry.delete(0, tk.END)
            entry.insert(0, recipe[field] or "")
        self.items_tree.delete(*self.items_tree.get_children())
        for item in db.get_recipe_items(self.current_id):
            self.items_tree.insert(
                "",
                "end",
                values=(
                    item["ingredient_kind"],
                    item["label"],
                    item["tobacco_classification"] or "",
                    item["tobacco_strength"] or "",
                    item["tobacco_cut"] or "",
                    item["tobacco_cut_size_mm"] or "",
                    number_text(item["percent"]),
                ),
            )
        self.update_total()

    def clear_form(self) -> None:
        self.current_id = None
        self.recipe_list.selection_clear(0, tk.END)
        for entry in self.fields.values():
            entry.delete(0, tk.END)
        self.items_tree.delete(*self.items_tree.get_children())
        self.tobacco_classification_var.set("")
        self.tobacco_strength_var.set("")
        self.tobacco_cut_var.set("")
        self.tobacco_cut_size_mm_var.set("")
        self.update_total()

    def on_item_select(self, _event: object | None = None) -> None:
        selection = self.items_tree.selection()
        if not selection:
            return
        kind, label, classification, strength, cut, cut_size_mm, percent = self.items_tree.item(selection[0], "values")
        self.kind_var.set(db.RECIPE_KIND_LABELS.get(kind, kind))
        self.label_var.set(label)
        self.tobacco_classification_var.set(classification)
        self.tobacco_strength_var.set(strength)
        self.tobacco_cut_var.set(cut)
        self.tobacco_cut_size_mm_var.set(cut_size_mm)
        self.percent_var.set(percent)
        self.update_tobacco_filter_state()

    def upsert_item(self) -> None:
        try:
            percent = db.parse_number(self.percent_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Процент должен быть числом.")
            return
        if percent is None or percent < 0:
            messagebox.showerror("Ошибка", "Процент должен быть числом не меньше 0.")
            return
        kind = self.selected_kind()
        classification = self.tobacco_classification_var.get().strip() if kind == "tobacco" else ""
        strength = self.tobacco_strength_var.get().strip() if kind == "tobacco" else ""
        cut = self.tobacco_cut_var.get().strip() if kind == "tobacco" else ""
        cut_size_mm = self.tobacco_cut_size_mm_var.get().strip() if kind == "tobacco" else ""
        label = self.label_var.get().strip() or classification or db.RECIPE_KIND_LABELS[kind]
        values = (kind, label, classification, strength, cut, cut_size_mm, number_text(percent))
        selection = self.items_tree.selection()
        if selection:
            self.items_tree.item(selection[0], values=values)
        else:
            self.items_tree.insert("", "end", values=values)
        self.percent_var.set("")
        self.update_total()

    def remove_item(self) -> None:
        for item_id in self.items_tree.selection():
            self.items_tree.delete(item_id)
        self.update_total()

    def recipe_values(self) -> dict[str, str]:
        return {field: entry.get().strip() for field, entry in self.fields.items()}

    def recipe_items(self) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for item_id in self.items_tree.get_children():
            kind, label, classification, strength, cut, cut_size_mm, percent = self.items_tree.item(item_id, "values")
            items.append(
                {
                    "ingredient_kind": kind,
                    "label": label,
                    "tobacco_classification": classification,
                    "tobacco_strength": strength,
                    "tobacco_cut": cut,
                    "tobacco_cut_size_mm": cut_size_mm,
                    "percent": percent,
                }
            )
        return items

    def update_total(self) -> None:
        total = 0.0
        for item in self.recipe_items():
            total += db.parse_number(item["percent"]) or 0
        self.total_label.configure(text=f"Сумма: {total:g}%")

    def save(self) -> None:
        try:
            recipe_id = db.save_recipe(self.recipe_values(), self.recipe_items(), self.current_id)
        except Exception as exc:
            messagebox.showerror("Не удалось сохранить рецепт", str(exc))
            return
        self.current_id = recipe_id
        self.refresh()
        self.app.after_data_changed()
        messagebox.showinfo("Сохранено", "Рецепт сохранён.")

    def delete(self) -> None:
        if self.current_id is None:
            messagebox.showwarning("Не выбрано", "Выберите рецепт для удаления.")
            return
        if not messagebox.askyesno("Удалить", "Удалить выбранный рецепт?"):
            return
        db.delete_recipe(self.current_id)
        self.clear_form()
        self.refresh()
        self.app.after_data_changed()


class CalculatorTab(ttk.Frame):
    def __init__(self, master: ttk.Notebook) -> None:
        super().__init__(master, padding=10)
        self.recipe_var = tk.StringVar()
        self.weight_var = tk.StringVar(value="1000")
        self.recipe_lookup: dict[str, int] = {}
        self.selection_vars: dict[int, tk.StringVar] = {}
        self.option_lookup: dict[int, dict[str, int | None]] = {}
        self._build()

    def _build(self) -> None:
        top = ttk.LabelFrame(self, text="Параметры расчёта", padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Рецепт").grid(row=0, column=0, sticky="w")
        self.recipe_combo = ttk.Combobox(top, textvariable=self.recipe_var, state="readonly", width=34)
        self.recipe_combo.grid(row=0, column=1, sticky="w", padx=6)
        self.recipe_combo.bind("<<ComboboxSelected>>", self.on_recipe_change)
        ttk.Label(top, text="Нужный объём, г").grid(row=0, column=2, sticky="w", padx=(18, 0))
        ttk.Entry(top, textvariable=self.weight_var, width=12).grid(row=0, column=3, sticky="w", padx=6)
        ttk.Button(top, text="Рассчитать", command=self.calculate).grid(row=0, column=4, padx=(12, 0))

        self.source_frame = ttk.LabelFrame(self, text="Выбор товаров по строкам рецепта", padding=10)
        self.source_frame.pack(fill="x", pady=8)
        self.source_frame.columnconfigure(1, weight=1)

        columns = ("label", "percent", "grams", "source", "price_g", "cost")
        self.result_tree = ttk.Treeview(self, columns=columns, show="headings", height=11)
        headers = {
            "label": "Ингредиент",
            "percent": "%",
            "grams": "Граммы",
            "source": "Выбранный товар",
            "price_g": "Цена/г",
            "cost": "Стоимость",
        }
        widths = {"label": 160, "percent": 70, "grams": 100, "source": 260, "price_g": 100, "cost": 110}
        for col in columns:
            self.result_tree.heading(col, text=headers[col])
            self.result_tree.column(col, width=widths[col], anchor="w")
        self.result_tree.pack(fill="both", expand=True)
        self.total_label = ttk.Label(self, text="Итого: -", font=("Segoe UI", 11, "bold"))
        self.total_label.pack(anchor="e", pady=(8, 0))

    def on_recipe_change(self, _event: object | None = None) -> None:
        self.refresh_sources()

    def refresh_recipe_choices(self) -> None:
        recipes = db.list_recipes()
        self.recipe_lookup = {row["name"]: row["id"] for row in recipes}
        names = list(self.recipe_lookup.keys())
        self.recipe_combo["values"] = names
        if names and self.recipe_var.get() not in names:
            self.recipe_var.set(names[0])
        if not names:
            self.recipe_var.set("")
        self.refresh_sources()

    def refresh_sources(self) -> None:
        previous = {key: var.get() for key, var in self.selection_vars.items()}
        self.selection_vars.clear()
        self.option_lookup.clear()
        for widget in self.source_frame.winfo_children():
            widget.destroy()

        recipe_name = self.recipe_var.get()
        if not recipe_name or recipe_name not in self.recipe_lookup:
            ttk.Label(self.source_frame, text="Рецепт не выбран").grid(row=0, column=0, sticky="w")
            return

        recipe_items = db.get_recipe_items(self.recipe_lookup[recipe_name])
        if not recipe_items:
            ttk.Label(self.source_frame, text="В рецепте нет строк").grid(row=0, column=0, sticky="w")
            return

        for row_index, recipe_item in enumerate(recipe_items):
            item_key = int(recipe_item["id"])
            kind = recipe_item["ingredient_kind"]
            kind_label = db.RECIPE_KIND_LABELS.get(kind, kind)
            filter_parts = []
            if kind == "tobacco":
                for field in ["tobacco_classification", "tobacco_strength", "tobacco_cut", "tobacco_cut_size_mm"]:
                    value = recipe_item[field]
                    if value:
                        filter_parts.append(str(value))
            filter_text = f" · {' / '.join(filter_parts)}" if filter_parts else ""
            title = f"{recipe_item['label']} · {kind_label}{filter_text} · {float(recipe_item['percent']):g}%"
            ttk.Label(self.source_frame, text=title).grid(row=row_index, column=0, sticky="w", pady=3)

            options = {"Не выбран": None}
            for packaging in db.packaging_options_for_recipe_item(recipe_item):
                price = f"{float(packaging['price_uah']) / float(packaging['package_amount_g']):.2f} грн/г"
                title = (
                    f"{packaging['item_name']} - "
                    f"{packaging['packaging_label'] or db.default_packaging_label(packaging['package_amount_g'])} "
                    f"/ {number_text(packaging['price_uah'])} грн ({price})"
                )
                options[title] = packaging["packaging_id"]

            var = tk.StringVar()
            values = list(options.keys())
            var.set(previous.get(item_key, values[0]) if previous.get(item_key) in options else values[0])
            combo = ttk.Combobox(self.source_frame, textvariable=var, state="readonly", values=values, width=58)
            combo.grid(row=row_index, column=1, sticky="ew", padx=(8, 0), pady=3)
            self.selection_vars[item_key] = var
            self.option_lookup[item_key] = options

    def calculate(self) -> None:
        if not self.recipe_var.get():
            messagebox.showwarning("Нет рецепта", "Выберите рецепт.")
            return
        try:
            total_weight = db.parse_number(self.weight_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Общий вес должен быть числом.")
            return
        if total_weight is None:
            messagebox.showerror("Ошибка", "Введите общий вес.")
            return

        recipe_id = self.recipe_lookup[self.recipe_var.get()]
        selections: dict[int, int | None] = {}
        for item_key, var in self.selection_vars.items():
            selections[item_key] = self.option_lookup.get(item_key, {}).get(var.get())
        try:
            rows, total_cost = db.calculate_recipe(recipe_id, total_weight, selections)
        except Exception as exc:
            messagebox.showerror("Ошибка расчёта", str(exc))
            return

        self.result_tree.delete(*self.result_tree.get_children())
        for row in rows:
            self.result_tree.insert(
                "",
                "end",
                values=(
                    row["label"],
                    f"{row['percent']:g}",
                    f"{row['grams']:.2f}",
                    row["selected_name"],
                    "неизвестно" if row["price_per_g"] is None else f"{row['price_per_g']:.4f}",
                    money(row["cost"]),
                ),
            )
        self.total_label.configure(text=f"Итого: {money(total_cost)}")


class ReferenceTab(ttk.Frame):
    def __init__(self, master: ttk.Notebook, app: "TobaccoMixApp") -> None:
        super().__init__(master, padding=10)
        self.app = app
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.classification_list = self._build_section(
            0,
            "Классификации табака",
            self.add_classification,
            self.rename_classification,
            self.delete_classification,
        )
        self.strength_list = self._build_section(
            1,
            "Крепость",
            self.add_strength,
            self.rename_strength,
            self.delete_strength,
        )
        self.cut_list = self._build_section(
            2,
            "Нарезка",
            self.add_cut,
            self.rename_cut,
            self.delete_cut,
        )

    def _build_section(self, column: int, title: str, add_cmd, rename_cmd, delete_cmd) -> tk.Listbox:
        frame = ttk.LabelFrame(self, text=title, padding=10)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 8) if column < 2 else (8, 0))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        listbox = tk.Listbox(frame, height=22)
        listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        listbox.configure(yscrollcommand=scrollbar.set)
        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Добавить", command=add_cmd).pack(side="left")
        ttk.Button(buttons, text="Переименовать", command=rename_cmd).pack(side="left", padx=6)
        ttk.Button(buttons, text="Удалить", command=delete_cmd).pack(side="left")
        return listbox

    def refresh(self) -> None:
        self.classifications = db.list_tobacco_classifications()
        self.strengths = db.list_tobacco_strengths()
        self.cuts = db.list_tobacco_cuts()
        self.classification_list.delete(0, tk.END)
        for row in self.classifications:
            self.classification_list.insert(tk.END, row["name"])
        self.strength_list.delete(0, tk.END)
        for row in self.strengths:
            self.strength_list.insert(tk.END, row["name"])
        self.cut_list.delete(0, tk.END)
        for row in self.cuts:
            self.cut_list.insert(tk.END, row["name"])

    def _selected_row(self, listbox: tk.Listbox, rows: list) -> object | None:
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Не выбрано", "Выберите значение в списке.")
            return None
        return rows[selection[0]]

    def _ask_name(self, title: str, prompt: str, initial: str = "") -> str | None:
        value = simpledialog.askstring(title, prompt, initialvalue=initial, parent=self)
        if value is None:
            return None
        value = value.strip()
        if not value:
            messagebox.showerror("Ошибка", "Название не может быть пустым.")
            return None
        return value

    def add_classification(self) -> None:
        name = self._ask_name("Новая классификация", "Название классификации:")
        if not name:
            return
        try:
            db.add_tobacco_classification(name)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self.after_reference_change()

    def rename_classification(self) -> None:
        row = self._selected_row(self.classification_list, self.classifications)
        if row is None:
            return
        name = self._ask_name("Переименовать классификацию", "Новое название:", row["name"])
        if not name:
            return
        try:
            db.rename_tobacco_classification(row["id"], name)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self.after_reference_change()

    def delete_classification(self) -> None:
        row = self._selected_row(self.classification_list, self.classifications)
        if row is None:
            return
        usage = db.tobacco_classification_usage(row["id"])
        message = f"Удалить классификацию '{row['name']}'?"
        if usage:
            message += f"\nОна используется в {usage} карточке(ах), связь будет удалена."
        if not messagebox.askyesno("Удалить классификацию", message):
            return
        db.delete_tobacco_classification(row["id"])
        self.after_reference_change()

    def add_strength(self) -> None:
        name = self._ask_name("Новая крепость", "Название крепости:")
        if not name:
            return
        try:
            db.add_tobacco_strength(name)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self.after_reference_change()

    def rename_strength(self) -> None:
        row = self._selected_row(self.strength_list, self.strengths)
        if row is None:
            return
        name = self._ask_name("Переименовать крепость", "Новое название:", row["name"])
        if not name:
            return
        try:
            db.rename_tobacco_strength(row["id"], name)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self.after_reference_change()

    def delete_strength(self) -> None:
        row = self._selected_row(self.strength_list, self.strengths)
        if row is None:
            return
        usage = db.tobacco_strength_usage(row["name"])
        message = f"Удалить крепость '{row['name']}'?"
        if usage:
            message += f"\nОна используется в {usage} карточке(ах), поле будет очищено."
        if not messagebox.askyesno("Удалить крепость", message):
            return
        db.delete_tobacco_strength(row["id"])
        self.after_reference_change()

    def add_cut(self) -> None:
        name = self._ask_name("Новая нарезка", "Название нарезки:")
        if not name:
            return
        try:
            db.add_tobacco_cut(name)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self.after_reference_change()

    def rename_cut(self) -> None:
        row = self._selected_row(self.cut_list, self.cuts)
        if row is None:
            return
        name = self._ask_name("Переименовать нарезку", "Новое название:", row["name"])
        if not name:
            return
        try:
            db.rename_tobacco_cut(row["id"], name)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self.after_reference_change()

    def delete_cut(self) -> None:
        row = self._selected_row(self.cut_list, self.cuts)
        if row is None:
            return
        usage = db.tobacco_cut_usage(row["name"])
        message = f"Удалить нарезку '{row['name']}'?"
        if usage:
            message += f"\nОна используется в {usage} записи(ях), поле будет очищено."
        if not messagebox.askyesno("Удалить нарезку", message):
            return
        db.delete_tobacco_cut(row["id"])
        self.after_reference_change()

    def after_reference_change(self) -> None:
        self.refresh()
        self.app.refresh_reference_data()
        self.app.after_data_changed()


class TobaccoMixApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Подбор ингредиентов и калькулятор смеси")
        self.geometry("1080x760")
        self.minsize(980, 680)
        self.sync = GoogleSheetsSynchronizer()
        self.first_run_remote_cache = initialize_local_database(self.sync)
        self.sync_status_var = tk.StringVar(value=self.initial_sync_status())
        self._sync_running = False
        self._sync_requested = False
        self._style()
        self.notebook = ttk.Notebook(self)
        self.status_bar = ttk.Frame(self, padding=(10, 4))
        self.status_bar.pack(side="bottom", fill="x")
        ttk.Label(self.status_bar, textvariable=self.sync_status_var).pack(side="left")
        ttk.Button(
            self.status_bar,
            text="Синхронизировать сейчас",
            command=lambda: self.schedule_sync(silent=False),
        ).pack(side="right")
        self.notebook.pack(side="top", fill="both", expand=True)
        self.ingredient_tabs: list[IngredientTab] = []
        for table_key, meta in db.ITEM_TABLES.items():
            tab = IngredientTab(self.notebook, table_key, self)
            self.ingredient_tabs.append(tab)
            self.notebook.add(tab, text=meta["label"])
        self.reference_tab = ReferenceTab(self.notebook, self)
        self.notebook.add(self.reference_tab, text="Справочники")
        self.recipes_tab = RecipesTab(self.notebook, self)
        self.notebook.add(self.recipes_tab, text="Рецепты")
        self.calculator_tab = CalculatorTab(self.notebook)
        self.notebook.add(self.calculator_tab, text="Калькулятор")
        self.refresh_recipe_choices()
        self.refresh_calculator_sources()
        self.after(100, lambda: self.schedule_sync(silent=not self.first_run_remote_cache))

    def _style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=24)
        style.configure("TNotebook.Tab", padding=(14, 6))

    def refresh_recipe_choices(self) -> None:
        if hasattr(self, "calculator_tab"):
            self.calculator_tab.refresh_recipe_choices()

    def refresh_calculator_sources(self) -> None:
        if hasattr(self, "calculator_tab"):
            self.calculator_tab.refresh_sources()

    def refresh_reference_data(self) -> None:
        for tab in getattr(self, "ingredient_tabs", []):
            if tab.table_key == "tobacco":
                tab.refresh_filter_options()
                tab.refresh()
        if hasattr(self, "recipes_tab"):
            self.recipes_tab.refresh_reference_options()
        self.refresh_calculator_sources()

    def initial_sync_status(self) -> str:
        if not self.sync.enabled:
            return "Синхронизация не настроена"
        if getattr(self, "first_run_remote_cache", False):
            return "Локальная база пуста, загружаю Google Таблицу"
        pending = self.sync.pending_count()
        return f"Ожидает отправки: {pending}" if pending else "Ожидает синхронизации"

    def after_data_changed(self) -> None:
        pending = self.sync.pending_count()
        if pending:
            self.sync_status_var.set(f"Ожидает отправки: {pending}")
        self.schedule_sync(silent=True)

    def schedule_sync(self, silent: bool = True) -> None:
        if self._sync_running:
            self._sync_requested = True
            return
        self._sync_running = True
        self.sync_status_var.set("Синхронизация...")

        def worker() -> None:
            result = self.sync.sync_once()
            self.after(0, lambda: self.finish_sync(result, silent))

        threading.Thread(target=worker, daemon=True).start()

    def finish_sync(self, result: SyncResult, silent: bool) -> None:
        self._sync_running = False
        self.sync_status_var.set(result.label())
        if result.ok and (result.pulled or result.conflicts):
            self.refresh_all_data()
        if result.conflicts:
            messagebox.showwarning(
                "Синхронизация",
                f"Google Таблица была главнее для {result.conflicts} конфликт(ов).\n"
                f"Подтянуто строк: {result.pulled}. Отправлено строк: {result.pushed}.",
            )
        elif not silent and result.status == "disabled":
            messagebox.showinfo("Синхронизация не настроена", result.message)
        elif not silent and not result.ok:
            title = "Данные не загружены" if getattr(self, "first_run_remote_cache", False) else "Синхронизация не выполнена"
            messagebox.showerror(title, result.message)
        elif not silent:
            messagebox.showinfo(
                "Синхронизация",
                f"Готово.\nПодтянуто строк: {result.pulled}. Отправлено строк: {result.pushed}.",
            )
        if result.ok and getattr(self, "first_run_remote_cache", False):
            self.first_run_remote_cache = False
        if self._sync_requested:
            self._sync_requested = False
            self.schedule_sync(silent=True)

    def refresh_all_data(self) -> None:
        for tab in getattr(self, "ingredient_tabs", []):
            tab.refresh()
        if hasattr(self, "reference_tab"):
            self.reference_tab.refresh()
        if hasattr(self, "recipes_tab"):
            self.recipes_tab.refresh()
        self.refresh_recipe_choices()
        self.refresh_calculator_sources()


if __name__ == "__main__":
    app = TobaccoMixApp()
    app.mainloop()
