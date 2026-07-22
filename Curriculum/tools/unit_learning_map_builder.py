"""Local Windows interface for composing custom student learning maps."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pypdf import PdfReader

import generate_unit_learning_map as learning_maps


MX_RED = "#CF003D"
INK = "#171717"
MUTED = "#666666"
PALE_RED = "#FFF4F7"
LINE = "#D8D8D8"


def set_app_identity() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
            "MiddlesexMathematics.StudentLearningMapBuilder"
        )
    except (AttributeError, OSError):
        pass


def open_pdf(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def print_pdf(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path, "print")  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["lp", str(path)])


def load_curriculum() -> tuple[list[dict], dict[str, list[dict]]]:
    courses = [
        learning_maps.parse_course(path)
        for path in sorted(learning_maps.COURSE_DIR.glob("math*.yaml"))
    ]
    _, skills_by_objective = learning_maps.load_skills()
    return courses, skills_by_objective


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").lower()
    return cleaned or "custom-unit"


def unique_output_path(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    counter = 2
    while candidate.exists():
        candidate = folder / f"{Path(filename).stem}-{counter}.pdf"
        counter += 1
    return candidate


def compose_custom_unit(course: dict, title: str, objectives: list[dict]) -> dict:
    return {
        "id": f"{course['id']}-CUSTOM",
        "title": title.strip(),
        "priority": "custom",
        "objectives": [
            {"id": objective["id"], "statement": objective["statement"]}
            for objective in objectives
        ],
    }


def default_pdf_filename(course: dict, title: str) -> str:
    return f"{course['id'].lower()}-{safe_filename(title)}-student-learning-objectives.pdf"


def generate_custom_map_to_path(
    course: dict,
    title: str,
    objectives: list[dict],
    skills_by_objective: dict[str, list[dict]],
    output_path: Path,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    custom_unit = compose_custom_unit(course, title, objectives)
    temporary = tempfile.NamedTemporaryFile(
        prefix="learning-map-",
        suffix=".pdf",
        dir=output_path.parent,
        delete=False,
    )
    temporary_path = Path(temporary.name)
    temporary.close()
    try:
        learning_maps.generate(
            course,
            custom_unit,
            skills_by_objective,
            temporary_path,
        )
        page_count = len(PdfReader(temporary_path).pages)
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return page_count


def generate_custom_map(
    course: dict,
    title: str,
    objectives: list[dict],
    skills_by_objective: dict[str, list[dict]],
    output_folder: Path,
) -> tuple[Path, int]:
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = unique_output_path(output_folder, default_pdf_filename(course, title))
    page_count = generate_custom_map_to_path(
        course,
        title,
        objectives,
        skills_by_objective,
        output_path,
    )
    return output_path, page_count


class LearningMapBuilder(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Student Learning Map Builder")
        icon_path = learning_maps.ROOT / "assets" / "student-learning-map-builder.png"
        if icon_path.exists():
            self._window_icon = tk.PhotoImage(file=str(icon_path))
            self.iconphoto(True, self._window_icon)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = min(1100, screen_width - 80)
        window_height = min(760, screen_height - 80)
        window_x = max(20, (screen_width - window_width) // 2)
        window_y = max(20, (screen_height - window_height) // 2)
        self.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
        self.minsize(min(920, screen_width - 40), min(650, screen_height - 40))
        self.configure(background="#FFFFFF")
        try:
            self.tk.call("tk", "scaling", 1.2)
        except tk.TclError:
            pass

        self.courses, self.skills_by_objective = load_curriculum()
        if not self.courses:
            raise RuntimeError("No curriculum course files were found.")

        self.course_by_label: dict[str, dict] = {}
        self.unit_by_label: dict[str, dict] = {}
        self.selected_objectives: list[dict] = []
        self.output_folder = Path.home() / "Documents" / "Student Learning Maps"

        self.course_var = tk.StringVar()
        self.start_unit_var = tk.StringVar()
        self.add_unit_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(self.output_folder))
        self.status_var = tk.StringVar(
            value="Choose an official unit to begin, then customize its objectives."
        )
        self.selection_var = tk.StringVar(value="0 objectives selected")
        self.unit_detail_var = tk.StringVar()

        self._configure_styles()
        self._build_interface()
        self._populate_courses()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("TFrame", background="#FFFFFF")
        style.configure("Panel.TFrame", background="#FFFFFF")
        style.configure("TLabel", background="#FFFFFF", foreground=INK, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Section.TLabel", foreground=MX_RED, font=("Segoe UI Semibold", 11))
        style.configure("TButton", font=("Segoe UI Semibold", 9), padding=(11, 7))
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=27)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9))
        style.configure("TCombobox", padding=4)

    def _build_interface(self) -> None:
        accent = tk.Frame(self, background=MX_RED, height=5)
        accent.grid(row=0, column=0, sticky="ew")
        accent.grid_propagate(False)

        header = tk.Frame(self, background="#FFFFFF", padx=28, pady=17)
        header.grid(row=1, column=0, sticky="ew")
        tk.Label(
            header,
            text="MIDDLESEX MATHEMATICS",
            background="#FFFFFF",
            foreground=MX_RED,
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Student Learning Map Builder",
            background="#FFFFFF",
            foreground=INK,
            font=("Georgia", 22, "bold"),
        ).pack(anchor="w", pady=(3, 0))
        tk.Frame(header, background=LINE, height=1).pack(fill="x", pady=(14, 0))

        content = ttk.Frame(self, padding=(26, 14, 26, 18))
        content.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

        setup = ttk.Frame(content)
        setup.grid(row=0, column=0, sticky="ew")
        setup.columnconfigure(0, weight=1)
        setup.columnconfigure(1, weight=2)

        ttk.Label(setup, text="COURSE", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(setup, text="START FROM UNIT", style="Section.TLabel").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Label(setup, text="MAP TITLE", style="Section.TLabel").grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )

        self.course_combo = ttk.Combobox(setup, textvariable=self.course_var, state="readonly")
        self.course_combo.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.course_combo.bind("<<ComboboxSelected>>", self._on_course_changed)

        self.start_unit_combo = ttk.Combobox(
            setup, textvariable=self.start_unit_var, state="readonly"
        )
        self.start_unit_combo.grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0)
        )

        self.title_entry = ttk.Entry(setup, textvariable=self.title_var)
        self.title_entry.grid(row=1, column=1, sticky="ew", padx=(16, 0), pady=(5, 0))

        unit_actions = ttk.Frame(content)
        unit_actions.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        ttk.Button(
            unit_actions,
            text="Start new map from selected unit",
            command=self._start_with_unit,
        ).pack(side="left")
        ttk.Label(
            unit_actions,
            text="This replaces the objectives currently on the map.",
            style="Muted.TLabel",
        ).pack(side="left", padx=(12, 0))

        output = ttk.Frame(content)
        output.grid(row=2, column=0, sticky="ew", pady=(0, 13))
        output.columnconfigure(0, weight=1)
        ttk.Label(output, text="PDF OUTPUT", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(output, textvariable=self.output_var, style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(3, 0)
        )
        output_actions = ttk.Frame(output)
        output_actions.grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Button(
            output_actions, text="Change folder", command=self._choose_output_folder
        ).pack(side="left")
        self.save_button = tk.Button(
            output_actions,
            text="Save PDF…",
            command=self._save_pdf,
            background=INK,
            foreground="#FFFFFF",
            activebackground="#303030",
            activeforeground="#FFFFFF",
            disabledforeground="#B5B5B5",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=14,
            pady=8,
            font=("Segoe UI Semibold", 9),
            cursor="hand2",
        )
        self.save_button.pack(side="left", padx=(7, 0))
        self.open_button = ttk.Button(
            output_actions,
            text="Save & Open",
            command=self._save_and_open,
        )
        self.open_button.pack(side="left", padx=(7, 0))
        self.print_button = ttk.Button(
            output_actions,
            text="Print to default",
            command=self._print_map,
        )
        self.print_button.pack(side="left", padx=(7, 0))
        self.output_buttons = [self.save_button, self.open_button, self.print_button]

        chooser = ttk.Panedwindow(content, orient="horizontal")
        chooser.grid(row=3, column=0, sticky="nsew")

        available_panel = ttk.Frame(chooser, style="Panel.TFrame", padding=(0, 0, 10, 0))
        selected_panel = ttk.Frame(chooser, style="Panel.TFrame", padding=(10, 0, 0, 0))
        chooser.add(available_panel, weight=1)
        chooser.add(selected_panel, weight=1)
        available_panel.columnconfigure(0, weight=1)
        available_panel.rowconfigure(2, weight=1)
        selected_panel.columnconfigure(0, weight=1)
        selected_panel.rowconfigure(1, weight=1)

        add_source = ttk.Frame(available_panel)
        add_source.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        add_source.columnconfigure(0, weight=1)
        ttk.Label(add_source, text="ADD FROM UNIT OR EXTENSION", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.add_unit_combo = ttk.Combobox(
            add_source, textvariable=self.add_unit_var, state="readonly"
        )
        self.add_unit_combo.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.add_unit_combo.bind("<<ComboboxSelected>>", self._on_add_unit_changed)
        ttk.Label(add_source, textvariable=self.unit_detail_var, style="Muted.TLabel").grid(
            row=2, column=0, sticky="w", pady=(3, 0)
        )

        available_heading = ttk.Frame(available_panel)
        available_heading.grid(row=1, column=0, sticky="ew", pady=(0, 7))
        ttk.Label(available_heading, text="Available objectives", style="Section.TLabel").pack(side="left")
        ttk.Label(
            available_heading,
            text="Select one or more, then add them.",
            style="Muted.TLabel",
        ).pack(side="right")

        self.available_tree = ttk.Treeview(
            available_panel,
            columns=("id", "statement"),
            show="headings",
            selectmode="extended",
        )
        self.available_tree.heading("id", text="Objective")
        self.available_tree.heading("statement", text="I can statement")
        self.available_tree.column("id", width=112, stretch=False)
        self.available_tree.column("statement", width=430, stretch=True)
        available_scroll = ttk.Scrollbar(
            available_panel, orient="vertical", command=self.available_tree.yview
        )
        self.available_tree.configure(yscrollcommand=available_scroll.set)
        self.available_tree.grid(row=2, column=0, sticky="nsew")
        available_scroll.grid(row=2, column=1, sticky="ns")
        self.available_tree.bind("<Double-1>", lambda _event: self._add_selected_available())

        available_actions = ttk.Frame(available_panel)
        available_actions.grid(row=3, column=0, sticky="ew", pady=(9, 0))
        ttk.Button(
            available_actions,
            text="Add entire unit",
            command=self._add_entire_unit,
        ).pack(side="left")
        ttk.Button(
            available_actions,
            text="Add selected objectives →",
            command=self._add_selected_available,
        ).pack(side="right")

        selected_heading = ttk.Frame(selected_panel)
        selected_heading.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        ttk.Label(selected_heading, text="Objectives on this map", style="Section.TLabel").pack(
            side="left"
        )
        ttk.Label(selected_heading, textvariable=self.selection_var, style="Muted.TLabel").pack(
            side="right"
        )

        self.selected_tree = ttk.Treeview(
            selected_panel,
            columns=("order", "id", "statement"),
            show="headings",
            selectmode="extended",
        )
        self.selected_tree.heading("order", text="#")
        self.selected_tree.heading("id", text="Objective")
        self.selected_tree.heading("statement", text="I can statement")
        self.selected_tree.column("order", width=38, stretch=False, anchor="center")
        self.selected_tree.column("id", width=112, stretch=False)
        self.selected_tree.column("statement", width=405, stretch=True)
        selected_scroll = ttk.Scrollbar(
            selected_panel, orient="vertical", command=self.selected_tree.yview
        )
        self.selected_tree.configure(yscrollcommand=selected_scroll.set)
        self.selected_tree.grid(row=1, column=0, sticky="nsew")
        selected_scroll.grid(row=1, column=1, sticky="ns")

        selected_actions = ttk.Frame(selected_panel)
        selected_actions.grid(row=2, column=0, sticky="ew", pady=(9, 0))
        ttk.Button(selected_actions, text="Move up", command=lambda: self._move_selected(-1)).pack(
            side="left"
        )
        ttk.Button(selected_actions, text="Move down", command=lambda: self._move_selected(1)).pack(
            side="left", padx=(7, 0)
        )
        ttk.Button(selected_actions, text="Remove", command=self._remove_selected).pack(
            side="right"
        )

        footer = ttk.Frame(content)
        footer.grid(row=4, column=0, sticky="ew", pady=(13, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")
        ttk.Label(
            footer,
            text="Custom maps do not alter the official curriculum.",
            style="Muted.TLabel",
        ).pack(side="right")

    def _populate_courses(self) -> None:
        self.course_by_label = {
            f"{course['number']} — {course['title']}": course for course in self.courses
        }
        labels = list(self.course_by_label)
        self.course_combo["values"] = labels
        self.course_var.set(labels[0])
        self._on_course_changed()

    def _current_course(self) -> dict:
        return self.course_by_label[self.course_var.get()]

    def _current_start_unit(self) -> dict:
        return self.unit_by_label[self.start_unit_var.get()]

    def _current_add_unit(self) -> dict:
        return self.unit_by_label[self.add_unit_var.get()]

    @staticmethod
    def _unit_label(unit: dict) -> str:
        priority = unit.get("priority", "required").title()
        return f"{unit['title']} · {priority}"

    def _on_course_changed(self, _event=None) -> None:
        course = self._current_course()
        self.unit_by_label = {self._unit_label(unit): unit for unit in course["units"]}
        labels = list(self.unit_by_label)
        self.start_unit_combo["values"] = labels
        self.add_unit_combo["values"] = labels
        self.start_unit_var.set(labels[0])
        self.add_unit_var.set(labels[0])
        self._on_add_unit_changed()
        self._start_with_unit()

    def _on_add_unit_changed(self, _event=None) -> None:
        unit = self._current_add_unit()
        self.unit_detail_var.set(
            f"{unit['id']} · {len(unit['objectives'])} objective"
            f"{'s' if len(unit['objectives']) != 1 else ''}"
        )
        self.available_tree.delete(*self.available_tree.get_children())
        for objective in unit["objectives"]:
            self.available_tree.insert(
                "",
                "end",
                iid=objective["id"],
                values=(objective["id"], objective["statement"]),
            )

    def _objective_with_source(self, objective: dict, unit: dict) -> dict:
        return {
            "id": objective["id"],
            "statement": objective["statement"],
            "source_unit_id": unit["id"],
            "source_unit_title": unit["title"],
        }

    def _start_with_unit(self) -> None:
        unit = self._current_start_unit()
        self.title_var.set(unit["title"])
        self.selected_objectives = [
            self._objective_with_source(objective, unit) for objective in unit["objectives"]
        ]
        self._refresh_selected()
        self.status_var.set(f"Started a new map from {unit['title']}.")

    def _add_objectives(self, objectives: list[dict], unit: dict) -> int:
        existing = {objective["id"] for objective in self.selected_objectives}
        additions = [
            self._objective_with_source(objective, unit)
            for objective in objectives
            if objective["id"] not in existing
        ]
        self.selected_objectives.extend(additions)
        self._refresh_selected(select_ids=[objective["id"] for objective in additions])
        return len(additions)

    def _add_entire_unit(self) -> None:
        unit = self._current_add_unit()
        added = self._add_objectives(unit["objectives"], unit)
        self.status_var.set(
            f"Added {added} objective{'s' if added != 1 else ''} from {unit['title']}."
        )

    def _add_selected_available(self) -> None:
        selected_ids = list(self.available_tree.selection())
        if not selected_ids:
            self.status_var.set("Select one or more available objectives first.")
            return
        unit = self._current_add_unit()
        by_id = {objective["id"]: objective for objective in unit["objectives"]}
        added = self._add_objectives([by_id[objective_id] for objective_id in selected_ids], unit)
        self.status_var.set(
            f"Added {added} objective{'s' if added != 1 else ''}; duplicates were skipped."
        )

    def _refresh_selected(self, select_ids: list[str] | None = None) -> None:
        self.selected_tree.delete(*self.selected_tree.get_children())
        for index, objective in enumerate(self.selected_objectives, start=1):
            self.selected_tree.insert(
                "",
                "end",
                iid=objective["id"],
                values=(index, objective["id"], objective["statement"]),
            )
        count = len(self.selected_objectives)
        self.selection_var.set(f"{count} objective{'s' if count != 1 else ''} selected")
        for objective_id in select_ids or []:
            if self.selected_tree.exists(objective_id):
                self.selected_tree.selection_add(objective_id)
                self.selected_tree.see(objective_id)

    def _remove_selected(self) -> None:
        selected_ids = set(self.selected_tree.selection())
        if not selected_ids:
            return
        self.selected_objectives = [
            objective
            for objective in self.selected_objectives
            if objective["id"] not in selected_ids
        ]
        self._refresh_selected()
        self.status_var.set(
            f"Removed {len(selected_ids)} objective{'s' if len(selected_ids) != 1 else ''}."
        )

    def _move_selected(self, direction: int) -> None:
        selected_ids = set(self.selected_tree.selection())
        if not selected_ids:
            return
        if direction < 0:
            indexes = range(1, len(self.selected_objectives))
            for index in indexes:
                current = self.selected_objectives[index]
                previous = self.selected_objectives[index - 1]
                if current["id"] in selected_ids and previous["id"] not in selected_ids:
                    self.selected_objectives[index - 1], self.selected_objectives[index] = current, previous
        else:
            indexes = range(len(self.selected_objectives) - 2, -1, -1)
            for index in indexes:
                current = self.selected_objectives[index]
                following = self.selected_objectives[index + 1]
                if current["id"] in selected_ids and following["id"] not in selected_ids:
                    self.selected_objectives[index], self.selected_objectives[index + 1] = following, current
        self._refresh_selected(select_ids=list(selected_ids))

    def _choose_output_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Choose where generated learning maps should be saved",
            initialdir=str(self.output_folder),
        )
        if selected:
            self.output_folder = Path(selected)
            self.output_var.set(str(self.output_folder))

    def _validate_map(self) -> str | None:
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Map title needed", "Enter a title for the learning map.")
            self.title_entry.focus_set()
            return None
        if not self.selected_objectives:
            messagebox.showwarning(
                "No objectives selected",
                "Add at least one learning objective before generating the map.",
            )
            return None
        return title

    def _set_output_buttons(self, state: str) -> None:
        for button in self.output_buttons:
            button.configure(state=state)

    def _create_pdf(self, output_path: Path | None = None) -> tuple[Path, int] | None:
        title = self._validate_map()
        if title is None:
            return None

        self._set_output_buttons("disabled")
        self.status_var.set("Generating the learning map…")
        self.update_idletasks()
        try:
            if output_path is None:
                output_path, page_count = generate_custom_map(
                    self._current_course(),
                    title,
                    self.selected_objectives,
                    self.skills_by_objective,
                    self.output_folder,
                )
            else:
                page_count = generate_custom_map_to_path(
                    self._current_course(),
                    title,
                    self.selected_objectives,
                    self.skills_by_objective,
                    output_path,
                )
        except RuntimeError as error:
            messagebox.showwarning(
                "Map is longer than two pages",
                "This selection does not fit the two-page format. Remove a few objectives "
                f"and try again.\n\n{error}",
            )
            self.status_var.set("The selection is too long for a two-page learning map.")
            return None
        except Exception as error:
            messagebox.showerror(
                "Could not generate the map",
                f"The PDF could not be created.\n\n{error}",
            )
            self.status_var.set("The PDF could not be generated.")
            return None
        else:
            self.status_var.set(
                f"Created {output_path.name} · {page_count} page{'s' if page_count != 1 else ''}."
            )
            return output_path, page_count
        finally:
            self._set_output_buttons("normal")

    def _save_pdf(self) -> None:
        title = self._validate_map()
        if title is None:
            return
        selected = filedialog.asksaveasfilename(
            title="Save student learning map",
            initialdir=str(self.output_folder),
            initialfile=default_pdf_filename(self._current_course(), title),
            defaultextension=".pdf",
            filetypes=[("PDF document", "*.pdf")],
        )
        if not selected:
            return
        output_path = Path(selected)
        self.output_folder = output_path.parent
        self.output_var.set(str(self.output_folder))
        result = self._create_pdf(output_path)
        if result:
            messagebox.showinfo("PDF saved", f"The learning map was saved here:\n\n{output_path}")

    def _save_and_open(self) -> None:
        result = self._create_pdf()
        if not result:
            return
        output_path, _page_count = result
        try:
            open_pdf(output_path)
        except OSError:
            messagebox.showinfo(
                "Learning map created",
                f"The PDF was saved here:\n\n{output_path}",
            )

    def _print_map(self) -> None:
        if self._validate_map() is None:
            return
        if not messagebox.askyesno(
            "Print learning map",
            "Generate the map and send it to the Windows default printer?\n\n"
            "A PDF copy will also be saved in the displayed output folder.",
        ):
            return
        result = self._create_pdf()
        if not result:
            return
        output_path, _page_count = result
        try:
            print_pdf(output_path)
            self.status_var.set(f"Sent {output_path.name} to the default printer.")
        except OSError:
            try:
                open_pdf(output_path)
            except OSError:
                pass
            messagebox.showwarning(
                "Default printing unavailable",
                "Windows could not send the PDF directly to the default printer. "
                f"The PDF was saved here instead:\n\n{output_path}",
            )


def main() -> None:
    set_app_identity()
    if "--self-test" in sys.argv:
        argument_index = sys.argv.index("--self-test")
        output_folder = (
            Path(sys.argv[argument_index + 1])
            if len(sys.argv) > argument_index + 1
            else Path.cwd()
        )
        output_folder.mkdir(parents=True, exist_ok=True)
        try:
            courses, skills_by_objective = load_curriculum()
            course = next(course for course in courses if course["id"] == "M32")
            units = {unit["id"]: unit for unit in course["units"]}
            objectives = [
                *units["M32-TRI"]["objectives"],
                *units["M32-TRX"]["objectives"],
            ]
            output_path, page_count = generate_custom_map(
                course,
                "Packaged Builder Self Test",
                objectives,
                skills_by_objective,
                output_folder,
            )
            (output_folder / "self-test-result.txt").write_text(
                f"PASS\n{output_path}\n{page_count} page(s)\n",
                encoding="utf-8",
            )
        except Exception:
            (output_folder / "self-test-result.txt").write_text(
                f"FAIL\n{traceback.format_exc()}",
                encoding="utf-8",
            )
            raise
        return

    try:
        app = LearningMapBuilder()
    except Exception as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Student Learning Map Builder",
            f"The builder could not start.\n\n{error}",
        )
        root.destroy()
        raise
    app.mainloop()


if __name__ == "__main__":
    main()
