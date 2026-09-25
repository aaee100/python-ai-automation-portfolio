

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pandas as pd
from datetime import date
from pathlib import Path
import json
import os
import numbers

# --- File setup ---

# Folder where expense_tracker.py is located
BASE_DIR = Path(__file__).parent

# Create a data folder next to the program
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

csv_file = DATA_DIR / "expenses.csv"
categories_file = DATA_DIR / "categories.json"

# --- Defaults ---
DEFAULT_CATEGORIES = {
    "Food": ["Groceries", "Restaurant", "Snacks"],
    "Transport": ["Bus Ticket", "Taxi", "Gasoline", "Train"],
    "Entertainment": ["Movie", "Concert", "Streaming Subscription"],
    "Utilities": ["Electric Bill", "Water Bill", "Internet Bill"],
    "Shopping": ["Clothes", "Electronics", "Shoes"],
    "Health": ["Pharmacy", "Dentist", "Gym Membership"],
    "Education": ["Course", "Books", "Online Course"],
    "Other": ["Misc"]
}

# --- Helper functions for storage ---
def load_categories():
    """Load category->descriptions mapping from categories.json or create default."""
    if categories_file.exists():
        try:
            with open(categories_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure mapping values are lists
            for k, v in list(data.items()):
                if not isinstance(v, list):
                    data[k] = list(v) if v is not None else []
            return data
        except Exception:
            # If file corrupt, recreate from defaults
            save_categories(DEFAULT_CATEGORIES)
            return dict(DEFAULT_CATEGORIES)
    else:
        save_categories(DEFAULT_CATEGORIES)
        return dict(DEFAULT_CATEGORIES)

def save_categories(mapping):
    """Save mapping dict to categories.json sorted by category name."""
    data = {k: sorted(list(set(v)), key=str.lower) for k, v in mapping.items()}
    data_sorted = dict(sorted(data.items(), key=lambda x: x[0].lower()))
    with open(categories_file, "w", encoding="utf-8") as f:
        json.dump(data_sorted, f, ensure_ascii=False, indent=2)

# --- Expense CSV helpers ---
def load_expenses():
    """Load CSV into DataFrame; ensure Date is datetime and Amount numeric rounded."""
    if csv_file.exists():
        df = pd.read_csv(csv_file)
        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0).round(2)
            df = df.sort_values("Date").reset_index(drop=True)
        return df
    else:
        return pd.DataFrame(columns=["Date", "Category", "Description", "Amount"])

def save_expenses(df):
    """Save DataFrame sorted by Date with Amount rounded."""
    df = df.copy()
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0).round(2)
    if "Date" in df.columns:
        df = df.sort_values("Date").reset_index(drop=True)
    df.to_csv(csv_file, index=False)

# --- Load or create categories mapping ---
categories = load_categories()

# Utility to update combobox options
def refresh_comboboxes():
    global categories
    cat_list = sorted(categories.keys(), key=str.lower)
    combo_category["values"] = cat_list
    # If current selected category exists, update descriptions list for it
    sel_cat = combo_category.get().strip()
    if sel_cat in categories:
        combo_description["values"] = categories[sel_cat]
    else:
        # fallback: union of all descriptions
        all_desc = sorted({d for vals in categories.values() for d in vals}, key=str.lower)
        combo_description["values"] = all_desc

# --- GUI action functions ---
def on_category_selected(event=None):
    """Update description dropdown to show only descriptions fitting the selected category."""
    sel = combo_category.get().strip()
    if sel in categories:
        combo_description["values"] = categories[sel]
    else:
        # if custom category typed, allow empty desc list (user may type a new description)
        combo_description["values"] = []

def add_expense():
    """Add or append an expense; create new category/description entries if necessary."""
    date_str = entry_date.get().strip()
    category = combo_category.get().strip()
    description = combo_description.get().strip()
    amount_text = entry_amount.get().strip()

    # Validation
    if not date_str or not category or not description or not amount_text:
        messagebox.showerror("Error", "Please fill in all fields.")
        return
    try:
        expense_date = pd.to_datetime(date_str)
    except Exception:
        messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
        return
    try:
        amount = float(amount_text)
        amount = round(amount, 2)
    except ValueError:
        messagebox.showerror("Error", "Amount must be a number.")
        return

    # If new category typed, add it
    if category not in categories:
        categories[category] = []
    # If new description not in that category, add it
    if description not in categories.get(category, []):
        categories[category].append(description)
        save_categories(categories)
        refresh_comboboxes()

    # Append expense row
    df = load_expenses()
    new_row = pd.DataFrame([{
        "Date": expense_date,
        "Category": category,
        "Description": description,
        "Amount": amount
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    save_expenses(df)
    update_total()
    messagebox.showinfo("Success", f"Expense added and saved to {csv_file.name}")
    clear_fields()

def clear_fields():
    combo_category.set("")
    combo_description.set("")
    entry_amount.delete(0, tk.END)
    entry_date.delete(0, tk.END)
    entry_date.insert(0, date.today().isoformat())

def update_total():
    df = load_expenses()
    total = df["Amount"].sum() if not df.empty else 0.0
    total = round(float(total), 2)
    label_total.config(text=f"Total Spent: ${total:,.2f}")

def view_expenses():
    df = load_expenses()
    if df.empty:
        messagebox.showinfo("Info", "No expenses recorded yet.")
        return

    win = tk.Toplevel(root)
    win.title("All Expenses")
    win.geometry("700x380")

    frame = tk.Frame(win)
    frame.pack(fill=tk.BOTH, expand=True)

    columns = ["Date", "Category", "Description", "Amount"]
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=160, anchor="center")

    vsb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = tk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscroll=vsb.set, xscroll=hsb.set)
    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")
    tree.pack(fill=tk.BOTH, expand=True)

    for _, row in df.iterrows():
        date_val = row["Date"].date() if not pd.isna(row["Date"]) else ""
        amount_formatted = f"{row['Amount']:.2f}"
        tree.insert("", tk.END, values=[date_val, row["Category"], row["Description"], amount_formatted])

def view_totals():
    df = load_expenses()
    if df.empty:
        messagebox.showinfo("Info", "No expenses to analyze.")
        return

    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    month_sum = df.groupby("Month", as_index=False)["Amount"].sum().round(2)
    year_sum = df.groupby("Year", as_index=False)["Amount"].sum().round(2)
    cat_sum = df.groupby("Category", as_index=False)["Amount"].sum().round(2)
    desc_sum = df.groupby("Description", as_index=False)["Amount"].sum().round(2)
    cat_year_sum = df.groupby(["Year", "Category"], as_index=False)["Amount"].sum().round(2)
    cat_month_sum = df.groupby(["Month", "Category"], as_index=False)["Amount"].sum().round(2)

    # Convert Year columns to clean strings (no .0)
    if "Year" in year_sum.columns:
        year_sum["Year"] = year_sum["Year"].apply(lambda x: str(int(x)) if pd.notna(x) else "")
    if "Year" in cat_year_sum.columns:
        cat_year_sum["Year"] = cat_year_sum["Year"].apply(lambda x: str(int(x)) if pd.notna(x) else "")

    # Sort sensibly
    month_sum = month_sum.sort_values("Month")
    year_sum = year_sum.sort_values("Year")
    cat_sum = cat_sum.sort_values("Amount", ascending=False)
    desc_sum = desc_sum.sort_values("Amount", ascending=False)
    cat_year_sum = cat_year_sum.sort_values(["Year", "Category"])
    cat_month_sum = cat_month_sum.sort_values(["Month", "Category"])

    win = tk.Toplevel(root)
    win.title("Expense Summary (Detailed)")
    win.geometry("760x500")

    notebook = ttk.Notebook(win)
    notebook.pack(fill=tk.BOTH, expand=True)

    def add_table(tab_name, grouped_df):
        frame = tk.Frame(notebook)
        notebook.add(frame, text=tab_name)
        cols = list(grouped_df.columns)
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=160, anchor="center")
        vsb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill=tk.BOTH, expand=True)
        for _, row in grouped_df.iterrows():
            row_vals = []
            for col in cols:
                if col == "Amount":
                    row_vals.append(f"{row[col]:.2f}")
                else:
                    row_vals.append(row[col])
            tree.insert("", tk.END, values=row_vals)

    add_table("By Month", month_sum)
    add_table("By Year", year_sum)

    # --- BY CATEGORY TAB ---
    tab_category = ttk.Frame(notebook)
    notebook.add(tab_category, text="By Category")

    sort_mode_cat = tk.StringVar(value="amount")

    tree_cat = ttk.Treeview(tab_category, columns=("Category", "Amount"), show="headings")
    tree_cat.heading("Category", text="Category")
    tree_cat.heading("Amount", text="Amount")
    tree_cat.column("Category", width=200)
    tree_cat.column("Amount", width=120, anchor="e")
    tree_cat.pack(fill="both", expand=True, padx=10, pady=(5, 0))

    def safe_to_float(x):
        """Convert safely to float, or return 0 if not numeric."""
        try:
            if isinstance(x, numbers.Number):
                return float(x)
            return float(str(x).strip().replace(",", "."))
        except Exception:
            return 0.0

    def extract_summary_items(data_obj):
        """Return list of (label, value) pairs from Series, DataFrame, or dict."""
        try:
            import pandas as pd

            # --- Case 1: pandas DataFrame ---
            if isinstance(data_obj, pd.DataFrame):
                # If there are two columns like ['Category', 'Amount']
                if "Amount" in data_obj.columns:
                    # Prefer a 'Category' or 'Description' column if present
                    label_col = None
                    for name in ("Category", "Description"):
                        if name in data_obj.columns:
                            label_col = name
                            break

                    if label_col:
                        return [
                            (str(row[label_col]), float(row["Amount"]))
                            for _, row in data_obj.iterrows()
                        ]
                    else:
                        # Fallback: use index
                        return [(str(idx), float(val)) for idx, val in data_obj["Amount"].items()]

                # If single-column DataFrame (e.g., grouped Series)
                if len(data_obj.columns) == 1:
                    col = data_obj.columns[0]
                    return [(str(idx), float(val)) for idx, val in data_obj[col].items()]

                # If nested dict-like DataFrame
                return [
                    (str(idx), float(sum(safe_to_float(v) for v in row.values())))
                    for idx, row in data_obj.to_dict(orient="index").items()
                ]

            # --- Case 2: pandas Series ---
            if isinstance(data_obj, pd.Series):
                return [(str(idx), float(val)) for idx, val in data_obj.items()]

            # --- Case 3: dict (possibly nested) ---
            if isinstance(data_obj, dict):
                first_val = next(iter(data_obj.values()))
                if isinstance(first_val, dict):
                    return [
                        (str(k), float(sum(safe_to_float(vv) for vv in v.values())))
                        for k, v in data_obj.items()
                    ]
                else:
                    return [(str(k), safe_to_float(v)) for k, v in data_obj.items()]

        except Exception as e:
            print("Error parsing summary:", e)

        return []

    def refresh_category_view():
        tree_cat.delete(*tree_cat.get_children())

        items = extract_summary_items(cat_sum)

        # Sorting
        if sort_mode_cat.get() == "amount":
            items.sort(key=lambda x: x[1], reverse=True)
        else:
            items.sort(key=lambda x: x[0].lower())

        for cat, val in items:
            tree_cat.insert("", "end", values=(cat, f"{val:,.2f}"))

    def toggle_category_sort():
        if sort_mode_cat.get() == "amount":
            sort_mode_cat.set("alpha")
            btn_sort_cat.config(text="Sort by Amount ↓")
        else:
            sort_mode_cat.set("amount")
            btn_sort_cat.config(text="Sort A–Z ↓")
        refresh_category_view()

    btn_sort_cat = tk.Button(tab_category, text="Sort A–Z ↓", command=toggle_category_sort)
    btn_sort_cat.pack(anchor="e", padx=10, pady=5)

    refresh_category_view()

    # --- BY DESCRIPTION TAB ---
    tab_description = ttk.Frame(notebook)
    notebook.add(tab_description, text="By Description")

    sort_mode_desc = tk.StringVar(value="amount")

    tree_desc = ttk.Treeview(tab_description, columns=("Description", "Amount"), show="headings")
    tree_desc.heading("Description", text="Description")
    tree_desc.heading("Amount", text="Amount")
    tree_desc.column("Description", width=220)
    tree_desc.column("Amount", width=120, anchor="e")
    tree_desc.pack(fill="both", expand=True, padx=10, pady=(5, 0))

    def refresh_description_view():
        tree_desc.delete(*tree_desc.get_children())

        items = extract_summary_items(desc_sum)

        if sort_mode_desc.get() == "amount":
            items.sort(key=lambda x: x[1], reverse=True)
        else:
            items.sort(key=lambda x: x[0].lower())

        for desc, val in items:
            tree_desc.insert("", "end", values=(desc, f"{val:,.2f}"))

    def toggle_description_sort():
        if sort_mode_desc.get() == "amount":
            sort_mode_desc.set("alpha")
            btn_sort_desc.config(text="Sort by Amount ↓")
        else:
            sort_mode_desc.set("amount")
            btn_sort_desc.config(text="Sort A–Z ↓")
        refresh_description_view()

    btn_sort_desc = tk.Button(tab_description, text="Sort A–Z ↓", command=toggle_description_sort)
    btn_sort_desc.pack(anchor="e", padx=10, pady=5)

    refresh_description_view()

    add_table("By Category & Year", cat_year_sum)
    add_table("By Category & Month", cat_month_sum)

# --- Manage Categories window ---

def open_manage_window():
    win = tk.Toplevel(root)
    win.title("Manage Categories")
    win.geometry("780x460")
    win.attributes('-toolwindow', False)

    left_frame = tk.Frame(win)
    left_frame.pack(side="left", fill="both", expand=False, padx=8, pady=8)
    right_frame = tk.Frame(win)
    right_frame.pack(side="left", fill="both", expand=True, padx=8, pady=8)

    tk.Label(left_frame, text="Categories:").pack(anchor="w")
    cat_listbox = tk.Listbox(left_frame, width=28, height=20, exportselection=False)
    cat_listbox.pack(fill="y", expand=False)

    tk.Label(right_frame, text="Descriptions for selected category:").pack(anchor="w")
    desc_listbox = tk.Listbox(right_frame, width=40, height=15, exportselection=False)
    desc_listbox.pack(fill="both", expand=True)

    refreshing = {"in_progress": False}

    def get_selected_category():
        try:
            idx = cat_listbox.curselection()
            if idx:
                return cat_listbox.get(idx[0])
        except Exception:
            pass
        return None

    def get_selected_description():
        try:
            idx = desc_listbox.curselection()
            if idx:
                return desc_listbox.get(idx[0])
        except Exception:
            pass
        return None

    def refresh_listboxes(select_cat=None, select_desc=None):
        refreshing["in_progress"] = True
        cat_listbox.delete(0, tk.END)
        for c in sorted(categories.keys(), key=str.lower):
            cat_listbox.insert(tk.END, c)
        if select_cat and select_cat in categories:
            idx = sorted(categories.keys(), key=str.lower).index(select_cat)
            cat_listbox.selection_set(idx)
        elif cat_listbox.size() > 0:
            cat_listbox.selection_set(0)
        fill_descriptions(restore_desc=select_desc)
        refreshing["in_progress"] = False

    def fill_descriptions(restore_desc=None):
        refreshing["in_progress"] = True
        desc_listbox.delete(0, tk.END)
        cat = get_selected_category()
        if cat and cat in categories:
            for d in categories[cat]:
                desc_listbox.insert(tk.END, d)
            if restore_desc and restore_desc in categories[cat]:
                idx = categories[cat].index(restore_desc)
                desc_listbox.selection_set(idx)
        refreshing["in_progress"] = False

    def on_cat_select(event=None):
        if refreshing["in_progress"]:
            return
        fill_descriptions()

    # ----- Inline Renaming -----
    def rename_inline(event):
        widget = event.widget
        if widget == cat_listbox:
            sel = get_selected_category()
            if not sel:
                return
            new = simpledialog.askstring("Rename Category", f"Rename '{sel}' to:", parent=win, initialvalue=sel)
            if new and new.strip():
                new = new.strip()
                if new != sel:
                    categories[new] = categories.pop(sel)
                    save_categories(categories)
                    refresh_comboboxes()
                    refresh_listboxes(select_cat=new)
        elif widget == desc_listbox:
            sel_cat = get_selected_category()
            sel_desc = get_selected_description()
            if not (sel_cat and sel_desc):
                return
            new = simpledialog.askstring("Rename Description", f"Rename '{sel_desc}' to:", parent=win, initialvalue=sel_desc)
            if new and new.strip():
                new = new.strip()
                if new != sel_desc:
                    lst = categories[sel_cat]
                    idx = lst.index(sel_desc)
                    lst[idx] = new
                    save_categories(categories)
                    refresh_comboboxes()
                    refresh_listboxes(select_cat=sel_cat, select_desc=new)

    cat_listbox.bind("<Double-1>", rename_inline)
    desc_listbox.bind("<Double-1>", rename_inline)

    # ---- Operations ----
    def add_category():
        name = simpledialog.askstring("Add Category", "Enter new category name:", parent=win)
        if name:
            name = name.strip()
            if not name or name in categories:
                return
            categories[name] = []
            save_categories(categories)
            refresh_comboboxes()
            refresh_listboxes(select_cat=name)

    def delete_category():
        sel = get_selected_category()
        if not sel:
            messagebox.showerror("Error", "Select a category to delete.", parent=win)
            return
        if messagebox.askyesno("Confirm", f"Delete '{sel}' and all its descriptions?", parent=win):
            categories.pop(sel, None)
            save_categories(categories)
            refresh_comboboxes()
            refresh_listboxes()

    def add_description():
        sel_cat = get_selected_category()
        if not sel_cat:
            messagebox.showerror("Error", "Select a category first.", parent=win)
            return
        name = simpledialog.askstring("Add Description", "Enter new description:", parent=win)
        if name:
            name = name.strip()
            if not name or name in categories[sel_cat]:
                return
            categories[sel_cat].append(name)
            save_categories(categories)
            refresh_comboboxes()
            refresh_listboxes(select_cat=sel_cat, select_desc=name)

    def delete_description():
        sel_cat = get_selected_category()
        sel_desc = get_selected_description()
        if not (sel_cat and sel_desc):
            messagebox.showerror("Error", "Select a description to delete.", parent=win)
            return
        if messagebox.askyesno("Confirm", f"Delete '{sel_desc}' from '{sel_cat}'?", parent=win):
            categories[sel_cat].remove(sel_desc)
            save_categories(categories)
            refresh_comboboxes()
            refresh_listboxes(select_cat=sel_cat)

    def move_description():
        sel_cat = get_selected_category()
        sel_desc = get_selected_description()
        if not (sel_cat and sel_desc):
            messagebox.showerror("Error", "Select a description to move.", parent=win)
            return

        move_win = tk.Toplevel(win)
        move_win.title("Move Description")
        move_win.geometry("300x150")
        tk.Label(move_win, text=f"Move '{sel_desc}' from '{sel_cat}' to:").pack(pady=8)

        combo_target = ttk.Combobox(move_win, values=sorted(categories.keys()))
        combo_target.pack(pady=6)
        combo_target.set(sel_cat)

        def confirm_move():
            target = combo_target.get().strip()
            if not target:
                move_win.destroy()
                return
            if target not in categories:
                if messagebox.askyesno("Create?", f"Create category '{target}'?", parent=move_win):
                    categories[target] = []
                else:
                    return
            categories[sel_cat].remove(sel_desc)
            if sel_desc not in categories[target]:
                categories[target].append(sel_desc)
            save_categories(categories)
            refresh_comboboxes()
            refresh_listboxes(select_cat=target, select_desc=sel_desc)
            move_win.destroy()

        tk.Button(move_win, text="Move", command=confirm_move).pack(pady=10)
        move_win.transient(win)
        move_win.grab_set()
        move_win.focus_force()

    # Buttons
    btn_frame = tk.Frame(left_frame)
    btn_frame.pack(pady=6)
    tk.Button(btn_frame, text="Add Category", width=15, command=add_category).grid(row=0, column=0, padx=4, pady=2)
    tk.Button(btn_frame, text="Delete Category", width=15, command=delete_category).grid(row=1, column=0, padx=4, pady=2)

    btn_frame2 = tk.Frame(right_frame)
    btn_frame2.pack(pady=6)
    tk.Button(btn_frame2, text="Add Description", width=18, command=add_description).grid(row=0, column=0, padx=4, pady=2)
    tk.Button(btn_frame2, text="Delete Description", width=18, command=delete_description).grid(row=1, column=0, padx=4, pady=2)
    tk.Button(btn_frame2, text="Move Description", width=18, command=move_description).grid(row=2, column=0, padx=4, pady=2)

    cat_listbox.bind("<<ListboxSelect>>", on_cat_select)
    refresh_listboxes()
    win.focus_force()

# --- GUI setup ---
root = tk.Tk()
root.title("Expense Tracker")
root.geometry("520x520")
root.resizable(False, False)

tk.Label(root, text="Date (YYYY-MM-DD):").pack(pady=4)
entry_date = tk.Entry(root, width=30)
entry_date.pack()
entry_date.insert(0, date.today().isoformat())

tk.Label(root, text="Category:").pack(pady=4)
combo_category = ttk.Combobox(root, values=sorted(categories.keys(), key=str.lower), width=30)
combo_category.pack()
combo_category.bind("<<ComboboxSelected>>", on_category_selected)
combo_category.bind("<KeyRelease>", lambda e: on_category_selected())

tk.Label(root, text="Description:").pack(pady=4)
# description combobox updates on category selection
all_desc = sorted({d for vals in categories.values() for d in vals}, key=str.lower)
combo_description = ttk.Combobox(root, values=all_desc, width=30)
combo_description.pack()

tk.Label(root, text="Amount ($):").pack(pady=4)
entry_amount = tk.Entry(root, width=30)
entry_amount.pack()

tk.Button(root, text="Add Expense", command=add_expense, bg="#4CAF50", fg="white", width=20).pack(pady=8)
tk.Button(root, text="View All Expenses", command=view_expenses, bg="#0275d8", fg="white", width=20).pack(pady=2)
tk.Button(root, text="View Totals", command=view_totals, bg="#5bc0de", fg="white", width=20).pack(pady=2)
tk.Button(root, text="Manage Categories", command=open_manage_window, bg="#6f42c1", fg="white", width=20).pack(pady=2)
tk.Button(root, text="Clear Fields", command=clear_fields, bg="#f0ad4e", fg="white", width=20).pack(pady=2)

label_total = tk.Label(root, text="", font=("Arial", 12, "bold"))
label_total.pack(pady=20)
update_total()

# Start with comboboxes refreshed
refresh_comboboxes()

root.mainloop()


