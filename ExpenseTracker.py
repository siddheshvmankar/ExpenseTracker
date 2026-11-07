"""
SpendWise - Personal Expense Tracker

Features:
- Add and delete expenses
- Monthly expense dashboard
- Category-wise spending analysis
- Monthly budget tracking
- CSV export
- SQLite local database
- Matplotlib spending chart
""" 

import csv
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict
APP_DIR = Path.home() / '.spendwise'
APP_DIR.mkdir(exist_ok=True)
DB_PATH = APP_DIR / 'expenses.db'
CATEGORIES = ['Food', 'Transport', 'Shopping', 'Bills', 'Education', 'Health', 'Entertainment', 'Rent', 'Travel', 'Other']
BG = '#F3F6FB'
NAVY = '#172554'
BLUE = '#2563EB'
TEXT = '#172033'
MUTED = '#64748B'
WHITE = '#FFFFFF'
GREEN = '#15803D'
RED = '#B91C1C'

# ============================================================
# DATABASE CLASS
# ============================================================
class ExpenseDatabase:

    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("\n\n            CREATE TABLE IF NOT EXISTS expenses (\n\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n\n                spent_on TEXT NOT NULL,\n\n                title TEXT NOT NULL,\n\n                category TEXT NOT NULL,\n\n                amount REAL NOT NULL CHECK(amount > 0),\n\n                payment_method TEXT NOT NULL DEFAULT 'UPI',\n\n                notes TEXT DEFAULT ''\n\n            )\n\n        ")
        self.conn.execute('\n\n            CREATE TABLE IF NOT EXISTS settings (\n\n                key TEXT PRIMARY KEY,\n\n                value TEXT NOT NULL\n\n            )\n\n        ')
        self.conn.commit()

    def add(self, spent_on, title, category, amount, payment_method, notes):
        self.conn.execute('INSERT INTO expenses\n\n               (spent_on, title, category, amount, payment_method, notes)\n\n               VALUES (?, ?, ?, ?, ?, ?)', (spent_on, title, category, amount, payment_method, notes))
        self.conn.commit()

    def delete(self, expense_id):
        self.conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        self.conn.commit()

    def get_expenses(self, month='All'):
        if month == 'All':
            query = 'SELECT * FROM expenses ORDER BY spent_on DESC, id DESC'
            return self.conn.execute(query).fetchall()
        return self.conn.execute('SELECT * FROM expenses\n\n               WHERE substr(spent_on, 1, 7) = ?\n\n               ORDER BY spent_on DESC, id DESC', (month,)).fetchall()

    def month_total(self, month):
        row = self.conn.execute('SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE substr(spent_on,1,7)=?', (month,)).fetchone()
        return float(row['total'])

    def category_totals(self, month):
        rows = self.conn.execute('SELECT category, SUM(amount) AS total FROM expenses\n\n               WHERE substr(spent_on,1,7)=? GROUP BY category ORDER BY total DESC', (month,)).fetchall()
        return [(r['category'], float(r['total'])) for r in rows]

    def monthly_totals(self, count=6):
        rows = self.conn.execute('SELECT substr(spent_on,1,7) AS month, SUM(amount) AS total\n\n               FROM expenses GROUP BY month ORDER BY month DESC LIMIT ?', (count,)).fetchall()
        return [(r['month'], float(r['total'])) for r in reversed(rows)]

    def get_budget(self, month):
        row = self.conn.execute('SELECT value FROM settings WHERE key = ?', ('budget_' + month,)).fetchone()
        return float(row['value']) if row else 15000.0

    def set_budget(self, month, amount):
        self.conn.execute('INSERT INTO settings(key,value) VALUES(?,?)\n\n               ON CONFLICT(key) DO UPDATE SET value=excluded.value', ('budget_' + month, str(amount)))
        self.conn.commit()

    def close(self):
        self.conn.close()

# ============================================================
# MAIN APPLICATION CLASS
# ============================================================
class SpendWiseApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('SpendWise | Personal Expense Tracker')
        self.geometry('1180x760')
        self.minsize(980, 650)
        self.configure(bg=BG)
        self.db = ExpenseDatabase()
        self.selected_month = tk.StringVar(value=date.today().strftime('%Y-%m'))
        self._style()
        self._build_header()
        self._build_tabs()
        self.refresh_all()
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', padding=(18, 10), font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', WHITE)], foreground=[('selected', BLUE)])
        style.configure('Treeview', background=WHITE, fieldbackground=WHITE, foreground=TEXT, rowheight=30, borderwidth=0, font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background='#E8EEF8', foreground=NAVY, font=('Segoe UI', 9, 'bold'), padding=8)
        style.map('Treeview', background=[('selected', '#DBEAFE')], foreground=[('selected', NAVY)])
        style.configure('TCombobox', padding=6)
        style.configure('TEntry', padding=7)

    def _build_header(self):
        header = tk.Frame(self, bg=NAVY, padx=24, pady=18)
        header.pack(fill='x')
        left = tk.Frame(header, bg=NAVY)
        left.pack(side='left', fill='x', expand=True)
        tk.Label(left, text='◈  SpendWise', bg=NAVY, fg=WHITE, font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        tk.Label(left, text='Personal finance, made clearer.', bg=NAVY, fg='#CBD5E1', font=('Segoe UI', 10)).pack(anchor='w', pady=(3, 0))
        right = tk.Frame(header, bg=NAVY)
        right.pack(side='right')
        tk.Label(right, text='ANALYSIS MONTH', bg=NAVY, fg='#BFDBFE', font=('Segoe UI', 8, 'bold')).pack(anchor='w')
        month_frame = tk.Frame(right, bg=NAVY)
        month_frame.pack(anchor='e', pady=(5, 0))
        self.month_entry = ttk.Entry(month_frame, textvariable=self.selected_month, width=10)
        self.month_entry.pack(side='left', padx=(0, 8))
        tk.Button(month_frame, text='Apply', command=self.refresh_all, bg=BLUE, fg=WHITE, activebackground='#1D4ED8', activeforeground=WHITE, relief='flat', padx=12, pady=5, cursor='hand2').pack(side='left')

    def _build_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True, padx=18, pady=18)
        self.dashboard_tab = tk.Frame(self.tabs, bg=BG, padx=16, pady=16)
        self.expenses_tab = tk.Frame(self.tabs, bg=BG, padx=16, pady=16)
        self.analysis_tab = tk.Frame(self.tabs, bg=BG, padx=16, pady=16)
        self.tabs.add(self.dashboard_tab, text='  Dashboard  ')
        self.tabs.add(self.expenses_tab, text='  Transactions  ')
        self.tabs.add(self.analysis_tab, text='  Analysis & Budget  ')
        self._build_dashboard()
        self._build_expenses()
        self._build_analysis()

    def _card(self, parent, title, value='—', subtitle='', accent=BLUE):
        card = tk.Frame(parent, bg=WHITE, highlightbackground='#E2E8F0', highlightthickness=1, padx=16, pady=14)
        tk.Label(card, text=title.upper(), bg=WHITE, fg=MUTED, font=('Segoe UI', 8, 'bold')).pack(anchor='w')
        value_label = tk.Label(card, text=value, bg=WHITE, fg=TEXT, font=('Segoe UI', 21, 'bold'))
        value_label.pack(anchor='w', pady=(8, 3))
        sub_label = tk.Label(card, text=subtitle, bg=WHITE, fg=accent, font=('Segoe UI', 9))
        sub_label.pack(anchor='w')
        return (card, value_label, sub_label)

    def _build_dashboard(self):
        tk.Label(self.dashboard_tab, text='Your money at a glance', bg=BG, fg=TEXT, font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        tk.Label(self.dashboard_tab, text='Summary for the selected month.', bg=BG, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(3, 14))
        cards = tk.Frame(self.dashboard_tab, bg=BG)
        cards.pack(fill='x')
        self.total_card, self.total_value, self.total_sub = self._card(cards, 'Total expenses', '₹0', 'Selected month')
        self.budget_card, self.budget_value, self.budget_sub = self._card(cards, 'Budget remaining', '₹0', 'Monthly budget')
        self.count_card, self.count_value, self.count_sub = self._card(cards, 'Transactions', '0', 'Selected month')
        self.category_card, self.category_value, self.category_sub = self._card(cards, 'Top category', '—', 'Highest spend')
        for i, card in enumerate([self.total_card, self.budget_card, self.count_card, self.category_card]):
            card.grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 8, 0))
            cards.columnconfigure(i, weight=1)
        lower = tk.Frame(self.dashboard_tab, bg=BG)
        lower.pack(fill='both', expand=True, pady=(18, 0))
        recent_frame = tk.Frame(lower, bg=WHITE, highlightbackground='#E2E8F0', highlightthickness=1)
        recent_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        tk.Label(recent_frame, text='Recent transactions', bg=WHITE, fg=TEXT, font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=14, pady=12)
        self.recent_tree = self._make_tree(recent_frame, ('date', 'title', 'category', 'amount'), ('Date', 'Description', 'Category', 'Amount'), heights=9)
        self.recent_tree.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        quick = tk.Frame(lower, bg=WHITE, highlightbackground='#E2E8F0', highlightthickness=1, padx=18, pady=18, width=230)
        quick.pack(side='right', fill='y')
        quick.pack_propagate(False)
        tk.Label(quick, text='Quick actions', bg=WHITE, fg=TEXT, font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 12))
        self._button(quick, '+ Add expense', lambda: self.tabs.select(self.expenses_tab)).pack(fill='x', pady=5)
        self._button(quick, 'View analysis', lambda: self.tabs.select(self.analysis_tab), bg='#E0EAFE', fg=NAVY).pack(fill='x', pady=5)
        self._button(quick, 'Export to CSV', self.export_csv).pack(fill='x', pady=5)
        tk.Label(quick, text='Data is saved locally on this computer in an SQLite database.', bg=WHITE, fg=MUTED, wraplength=190, justify='left', font=('Segoe UI', 9)).pack(anchor='w', pady=(20, 0))

    def _button(self, parent, text, command, bg=BLUE, fg=WHITE):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief='flat', font=('Segoe UI', 10, 'bold'), padx=12, pady=9, cursor='hand2')

    def _make_tree(self, parent, columns, headings, heights=12):
        tree = ttk.Treeview(parent, columns=columns, show='headings', height=heights)
        widths = {'date': 105, 'title': 210, 'category': 130, 'amount': 120, 'payment': 110, 'notes': 220, 'id': 55}
        for col, heading in zip(columns, headings):
            tree.heading(col, text=heading)
            tree.column(col, width=widths.get(col, 120), anchor='w' if col in ('title', 'category', 'notes') else 'center')
        return tree

    def _build_expenses(self):
        tk.Label(self.expenses_tab, text='Manage transactions', bg=BG, fg=TEXT, font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        tk.Label(self.expenses_tab, text='Add a record below, then review or remove entries.', bg=BG, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(3, 12))
        form = tk.Frame(self.expenses_tab, bg=WHITE, padx=16, pady=14, highlightbackground='#E2E8F0', highlightthickness=1)
        form.pack(fill='x', pady=(0, 14))
        self.form_vars = {'date': tk.StringVar(value=date.today().isoformat()), 'title': tk.StringVar(), 'category': tk.StringVar(value=CATEGORIES[0]), 'amount': tk.StringVar(), 'payment': tk.StringVar(value='UPI'), 'notes': tk.StringVar()}
        fields = [('Date (YYYY-MM-DD)', 'date', 16), ('Description', 'title', 23), ('Category', 'category', 17), ('Amount (₹)', 'amount', 14), ('Payment method', 'payment', 15), ('Notes (optional)', 'notes', 23)]
        for i, (label, key, width) in enumerate(fields):
            col = i % 3
            row = i // 3 * 2
            tk.Label(form, text=label, bg=WHITE, fg=MUTED, font=('Segoe UI', 9, 'bold')).grid(row=row, column=col, sticky='w', padx=(0, 14), pady=(2, 5))
            if key == 'category':
                widget = ttk.Combobox(form, textvariable=self.form_vars[key], values=CATEGORIES, state='readonly', width=width)
            elif key == 'payment':
                widget = ttk.Combobox(form, textvariable=self.form_vars[key], values=['UPI', 'Cash', 'Card', 'Net Banking', 'Other'], state='readonly', width=width)
            else:
                widget = ttk.Entry(form, textvariable=self.form_vars[key], width=width)
            widget.grid(row=row + 1, column=col, sticky='ew', padx=(0, 14), pady=(0, 10))
            form.columnconfigure(col, weight=1)
        self._button(form, '＋ Save expense', self.add_expense).grid(row=2, column=2, sticky='e', pady=(4, 0))
        toolbar = tk.Frame(self.expenses_tab, bg=BG)
        toolbar.pack(fill='x', pady=(0, 8))
        tk.Label(toolbar, text='Transactions for selected month', bg=BG, fg=TEXT, font=('Segoe UI', 11, 'bold')).pack(side='left')
        self._button(toolbar, 'Delete selected', self.delete_expense, bg='#FEE2E2', fg=RED).pack(side='right')
        table_frame = tk.Frame(self.expenses_tab, bg=WHITE)
        table_frame.pack(fill='both', expand=True)
        cols = ('id', 'date', 'title', 'category', 'amount', 'payment', 'notes')
        self.expense_tree = self._make_tree(table_frame, cols, ('ID', 'Date', 'Description', 'Category', 'Amount (₹)', 'Payment', 'Notes'), heights=10)
        self.expense_tree.column('id', width=50)
        self.expense_tree.pack(fill='both', expand=True, padx=8, pady=8)

    def _build_analysis(self):
        tk.Label(self.analysis_tab, text='Spending analysis', bg=BG, fg=TEXT, font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        tk.Label(self.analysis_tab, text='Understand which categories take the largest share of your budget.', bg=BG, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(3, 12))
        budget = tk.Frame(self.analysis_tab, bg=WHITE, padx=16, pady=14, highlightbackground='#E2E8F0', highlightthickness=1)
        budget.pack(fill='x', pady=(0, 14))
        tk.Label(budget, text='Monthly budget (₹)', bg=WHITE, fg=TEXT, font=('Segoe UI', 10, 'bold')).pack(side='left')
        self.budget_input = tk.StringVar(value='15000')
        ttk.Entry(budget, textvariable=self.budget_input, width=14).pack(side='left', padx=10)
        self._button(budget, 'Save budget', self.save_budget).pack(side='left')
        self.budget_status = tk.Label(budget, text='', bg=WHITE, fg=MUTED, font=('Segoe UI', 10))
        self.budget_status.pack(side='left', padx=16)
        body = tk.Frame(self.analysis_tab, bg=BG)
        body.pack(fill='both', expand=True)
        category_frame = tk.Frame(body, bg=WHITE, padx=14, pady=14, highlightbackground='#E2E8F0', highlightthickness=1)
        category_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        tk.Label(category_frame, text='Category breakdown', bg=WHITE, fg=TEXT, font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        self.category_tree = self._make_tree(category_frame, ('category', 'amount', 'share'), ('Category', 'Total (₹)', 'Share'), heights=10)
        self.category_tree.pack(fill='both', expand=True)
        chart_frame = tk.Frame(body, bg=WHITE, padx=14, pady=14, highlightbackground='#E2E8F0', highlightthickness=1)
        chart_frame.pack(side='right', fill='both', expand=True)
        tk.Label(chart_frame, text='Visual insights', bg=WHITE, fg=TEXT, font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        self.chart_area = tk.Frame(chart_frame, bg=WHITE)
        self.chart_area.pack(fill='both', expand=True)
        self.chart_note = tk.Label(self.chart_area, text='Charts appear here when matplotlib is installed.\nInstall it with: pip install matplotlib', bg=WHITE, fg=MUTED, justify='center', font=('Segoe UI', 10))
        self.chart_note.pack(expand=True)

    def _validate_month(self):
        month = self.selected_month.get().strip()
        try:
            datetime.strptime(month, '%Y-%m')
            return month
        except ValueError:
            messagebox.showerror('Invalid month', 'Enter the month as YYYY-MM, for example 2026-10.')
            return None

    def add_expense(self):
        try:
            spent_on = self.form_vars['date'].get().strip()
            datetime.strptime(spent_on, '%Y-%m-%d')
            title = self.form_vars['title'].get().strip()
            category = self.form_vars['category'].get()
            amount = float(self.form_vars['amount'].get().strip())
            payment = self.form_vars['payment'].get()
            notes = self.form_vars['notes'].get().strip()
            if not title:
                raise ValueError('Enter a description.')
            if amount <= 0:
                raise ValueError('Amount must be greater than zero.')
            if not category or not payment:
                raise ValueError('Choose a category and payment method.')
            self.db.add(spent_on, title, category, amount, payment, notes)
            self.selected_month.set(spent_on[:7])
            self.form_vars['title'].set('')
            self.form_vars['amount'].set('')
            self.form_vars['notes'].set('')
            self.refresh_all()
            messagebox.showinfo('Saved', 'Expense saved successfully.')
        except ValueError as exc:
            messagebox.showerror('Check your input', str(exc) or 'Enter a valid date and amount.')
        except sqlite3.Error as exc:
            messagebox.showerror('Database error', f'Could not save the expense:\n{exc}')

    def delete_expense(self):
        selected = self.expense_tree.selection()
        if not selected:
            messagebox.showwarning('Select a transaction', 'Choose a transaction row first.')
            return
        row = self.expense_tree.item(selected[0], 'values')
        if messagebox.askyesno('Delete transaction', f"Delete '{row[2]}' for ₹{row[4]}?"):
            self.db.delete(int(row[0]))
            self.refresh_all()

    def save_budget(self):
        month = self._validate_month()
        if not month:
            return
        try:
            amount = float(self.budget_input.get().strip())
            if amount <= 0:
                raise ValueError
            self.db.set_budget(month, amount)
            self.refresh_all()
            messagebox.showinfo('Budget saved', f'Budget for {month} set to ₹{amount:,.2f}.')
        except ValueError:
            messagebox.showerror('Invalid budget', 'Enter a budget amount greater than zero.')

    def export_csv(self):
        month = self._validate_month()
        if not month:
            return
        rows = self.db.get_expenses(month)
        if not rows:
            messagebox.showinfo('Nothing to export', 'There are no transactions for this month.')
            return
        path = filedialog.asksaveasfilename(title='Export transactions', defaultextension='.csv', initialfile=f'spendwise_{month}.csv', filetypes=[('CSV files', '*.csv'), ('All files', '*.*')])
        if not path:
            return
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Date', 'Description', 'Category', 'Amount', 'Payment Method', 'Notes'])
            for r in rows:
                writer.writerow([r['id'], r['spent_on'], r['title'], r['category'], r['amount'], r['payment_method'], r['notes']])
        messagebox.showinfo('Export complete', f'CSV exported to:\n{path}')

    def refresh_all(self):
        month = self._validate_month()
        if not month:
            return
        rows = self.db.get_expenses(month)
        total = sum((float(r['amount']) for r in rows))
        budget = self.db.get_budget(month)
        remaining = budget - total
        by_category = defaultdict(float)
        for r in rows:
            by_category[r['category']] += float(r['amount'])
        top = max(by_category, key=by_category.get) if by_category else '—'
        self.total_value.config(text=f'₹{total:,.2f}')
        self.total_sub.config(text=month, fg=MUTED)
        self.budget_value.config(text=f'₹{remaining:,.2f}', fg=GREEN if remaining >= 0 else RED)
        self.budget_sub.config(text='Remaining' if remaining >= 0 else 'Over budget', fg=GREEN if remaining >= 0 else RED)
        self.count_value.config(text=str(len(rows)))
        self.count_sub.config(text=f"Transaction{('s' if len(rows) != 1 else '')}")
        self.category_value.config(text=top)
        self.category_sub.config(text=f'₹{by_category[top]:,.2f}' if top != '—' else 'No spending yet')
        for tree in (self.recent_tree, self.expense_tree, self.category_tree):
            for item in tree.get_children():
                tree.delete(item)
        for r in rows[:8]:
            self.recent_tree.insert('', 'end', values=(r['spent_on'], r['title'], r['category'], f"{float(r['amount']):,.2f}"))
        for r in rows:
            self.expense_tree.insert('', 'end', values=(r['id'], r['spent_on'], r['title'], r['category'], f"{float(r['amount']):,.2f}", r['payment_method'], r['notes'] or ''))
        for cat, amount in sorted(by_category.items(), key=lambda item: item[1], reverse=True):
            share = amount / total * 100 if total else 0
            self.category_tree.insert('', 'end', values=(cat, f'{amount:,.2f}', f'{share:.1f}%'))
        self.budget_input.set(f'{budget:.2f}'.rstrip('0').rstrip('.'))
        self.budget_status.config(text=f'Spent ₹{total:,.2f} of ₹{budget:,.2f}  •  {max(0, min(100, total / budget * 100)):.0f}% used', fg=RED if total > budget else GREEN)
        self._draw_charts(month, by_category, total)

    def _draw_charts(self, month, by_category, total):
        for child in self.chart_area.winfo_children():
            child.destroy()
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import matplotlib
            matplotlib.use('TkAgg')
        except Exception:
            self.chart_note = tk.Label(self.chart_area, text='Charts need matplotlib.\nRun: py -m pip install matplotlib', bg=WHITE, fg=MUTED, justify='center', font=('Segoe UI', 10))
            self.chart_note.pack(expand=True)
            return
        fig = Figure(figsize=(5.2, 4.0), dpi=95, facecolor=WHITE)
        ax = fig.add_subplot(111)
        if by_category:
            cats = list(by_category.keys())
            vals = list(by_category.values())
            ax.pie(vals, labels=cats, autopct='%1.0f%%', startangle=90, textprops={'fontsize': 8})
            ax.set_title(f'Category split — {month}', fontsize=11, color=TEXT, pad=10)
        else:
            ax.text(0.5, 0.5, 'Add expenses to see your spending chart', ha='center', va='center', wrap=True, color=MUTED)
            ax.axis('off')
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def on_close(self):
        self.db.close()
        self.destroy()
if __name__ == '__main__':
    app = SpendWiseApp()
    app.mainloop()
