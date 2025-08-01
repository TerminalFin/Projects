# === Parses data from the rated_disabilities API call at va.gov ===
# === Visit the below URL after logging in to va.gov to retrieve json data ===
# === https://api.va.gov/v0/rated_disabilities ===

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import pandas as pd
import os

class VAParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VA Disability Parser")
        self.root.geometry("900x600")

        self.data = pd.DataFrame()
        self.original_data = pd.DataFrame()
        self.filtered_data = pd.DataFrame()
        self.current_sort_col = None
        self.current_sort_desc = True
        self.search_var = tk.StringVar()
        self.service_var = tk.StringVar(value="All")
        self.static_var = tk.StringVar(value="All")

        self.setup_ui()

    def setup_ui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        open_btn = ttk.Button(top_frame, text="Open File", command=self.load_file)
        open_btn.pack(side=tk.LEFT, padx=(0, 10))

        export_btn = ttk.Button(top_frame, text="Export", command=self.export_prompt)
        export_btn.pack(side=tk.LEFT)

        reset_btn = ttk.Button(top_frame, text="Reset Sort", command=self.reset_sort)
        reset_btn.pack(side=tk.LEFT, padx=(10, 0))

        search_entry = ttk.Entry(top_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.RIGHT, padx=(5, 0))
        search_entry.bind("<KeyRelease>", self.apply_filters_and_search)

        ttk.Label(top_frame, text="Search:").pack(side=tk.RIGHT)

        filter_frame = ttk.LabelFrame(self.root, text="Filters")
        filter_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Label(filter_frame, text="Service Connection:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        service_combo = ttk.Combobox(filter_frame, textvariable=self.service_var, values=["All", "Service Connected", "Not Service Connected"], state="readonly", width=20)
        service_combo.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        service_combo.bind("<<ComboboxSelected>>", self.apply_filters_and_search)

        ttk.Label(filter_frame, text="Static Status:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        static_combo = ttk.Combobox(filter_frame, textvariable=self.static_var, values=["All", "Static", "Non-Static"], state="readonly", width=20)
        static_combo.grid(row=0, column=3, padx=5, pady=2, sticky="w")
        static_combo.bind("<<ComboboxSelected>>", self.apply_filters_and_search)

        self.tree = ttk.Treeview(self.root, columns=["Decision", "Rating %", "Condition", "Description", "Static"], show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        vsb = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))

        self.status = ttk.Label(self.root, text="Ready", anchor="w")
        self.status.pack(fill=tk.X, padx=5, pady=(0, 5))

    def load_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r") as f:
                json_data = json.load(f)
            ratings = json_data["data"]["attributes"]["individual_ratings"]
        except Exception as e:
            messagebox.showerror("Error", f"Could not load file:\n{e}")
            return

        self.status["text"] = f"Loaded: {os.path.basename(path)}"

        df = pd.DataFrame([
            {
                "Decision": r.get("decision"),
                "Rating %": r.get("rating_percentage"),
                "Condition": r.get("diagnostic_type_name"),
                "Description": r.get("diagnostic_text"),
                "Static": r.get("static_ind")
            }
            for r in ratings
        ])

        df["Rating %"] = df["Rating %"].fillna("N/A")
        df["Static"] = df["Static"].apply(lambda x: "Yes" if x is True else ("No" if x is False else "N/A"))

        self.data = df.copy()
        self.original_data = df.copy()
        self.filtered_data = df.copy()
        self.current_sort_col = None
        self.display_data(df, default_sort=True)

    def display_data(self, df, default_sort=False):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if default_sort:
            df = self.custom_default_sort(df)

        for _, row in df.iterrows():
            values = list(row.values)
            self.tree.insert("", "end", values=values)

    def custom_default_sort(self, df):
        def sort_key(row):
            decision = row["Decision"]
            pct = row["Rating %"]
            try:
                pct_val = float(pct) if pct != "N/A" else -1
            except:
                pct_val = -1
            service_conn_priority = 0 if decision == "Service Connected" else 1
            return (service_conn_priority, -pct_val)

        sorted_df = df.copy()
        sorted_df["__sort_key__"] = sorted_df.apply(sort_key, axis=1)
        sorted_df = sorted_df.sort_values("__sort_key__").drop(columns="__sort_key__")
        return sorted_df

    def sort_by_column(self, col):
        if self.filtered_data.empty:
            return

        desc = True
        if self.current_sort_col == col:
            desc = not self.current_sort_desc

        self.current_sort_col = col
        self.current_sort_desc = desc

        df = self.filtered_data.copy()
        try:
            df[col] = df[col].replace("N/A", -1).astype(float)
        except:
            pass

        df = df.sort_values(by=col, ascending=not desc)
        self.display_data(df)

    def apply_filters_and_search(self, event=None):
        df = self.original_data.copy()

        svc_filter = self.service_var.get()
        static_filter = self.static_var.get()

        if svc_filter == "Service Connected":
            df = df[df["Decision"] == "Service Connected"]
        elif svc_filter == "Not Service Connected":
            df = df[df["Decision"] == "Not Service Connected"]

        if static_filter == "Static":
            df = df[df["Static"] == "Yes"]
        elif static_filter == "Non-Static":
            df = df[df["Static"] == "No"]

        query = self.search_var.get().strip().lower()
        if query:
            df = df[df.apply(lambda row: query in str(row).lower(), axis=1)]

        self.filtered_data = df
        self.display_data(df, default_sort=True)

    def export_prompt(self):
        if self.filtered_data.empty:
            messagebox.showinfo("Export", "No data to export.")
            return

        prompt_text = (
            "Select export format by number:\n"
            "1 - CSV\n"
            "2 - TXT (tab-separated)\n"
            "3 - Markdown\n"
            "4 - XLSX"
        )
        choice = simpledialog.askstring("Export Format", prompt_text, parent=self.root)
        if not choice:
            return

        choice = choice.strip()
        if choice == "1":
            self.export_csv()
        elif choice == "2":
            self.export_txt()
        elif choice == "3":
            self.export_md()
        elif choice == "4":
            self.export_xlsx()
        else:
            messagebox.showerror("Export", "Invalid choice. Please enter 1, 2, 3, or 4.")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            self.filtered_data.to_csv(path, index=False)
            messagebox.showinfo("Export", f"CSV exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV:\n{e}")

    def export_txt(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not path:
            return
        try:
            self.filtered_data.to_csv(path, index=False, sep="\t")
            messagebox.showinfo("Export", f"Text file exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export text file:\n{e}")

    def export_md(self):
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown files", "*.md")])
        if not path:
            return
        try:
            md_table = self.filtered_data.to_markdown(index=False)
            with open(path, "w", encoding="utf-8") as f:
                f.write(md_table)
            messagebox.showinfo("Export", f"Markdown file exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export markdown file:\n{e}")

    def export_xlsx(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            self.filtered_data.to_excel(path, index=False)
            messagebox.showinfo("Export", f"Excel file exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export Excel file:\n{e}")

    def reset_sort(self):
        if not self.filtered_data.empty:
            self.display_data(self.filtered_data, default_sort=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = VAParserApp(root)
    root.mainloop()
