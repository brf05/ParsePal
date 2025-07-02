import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from parser import parse_db
from utils import find_sqlite_files
from PIL import Image, ImageTk
import os
import pandas as pd
import collections
import re

class ParsePalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ParsePal – DB Parser")

        self.folder_path = tk.StringVar()
        self.selected_app = tk.StringVar(value="WhatsApp")
        self.search_var = tk.StringVar()
        self.keyword_var = tk.StringVar()
        self.direction_var = tk.StringVar(value="All")
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.df = None
        self.filtered_df = None
        self.preview_windows = {}
        self.last_previewed_media = None  # <-- Add this line
        
        self.setup_ui()
        self.tree.bind("<<TreeviewSelect>>", self.on_message_select)

    def on_message_select(self, event):
        selected = self.tree.selection()
        if not selected or self.filtered_df is None:
            return

        index = self.tree.index(selected[0])
        row = self.filtered_df.iloc[index]
        media_path = row.get("media_path")

        # Only open if media_path is valid and different from last previewed
        if media_path and os.path.isfile(media_path):
            if (media_path != self.last_previewed_media or
                media_path not in self.preview_windows or
                not self.preview_windows[media_path].winfo_exists()):
                self.show_media_preview(media_path)
                self.last_previewed_media = media_path
        else:
            self.last_previewed_media = None

    def show_media_preview(self, filepath):
        # If already open, bring to front
        if filepath in self.preview_windows and self.preview_windows[filepath].winfo_exists():
            self.preview_windows[filepath].lift()
            return

        preview_win = tk.Toplevel(self.root)
        preview_win.title("Media Preview")
        self.preview_windows[filepath] = preview_win  # Track window

        def on_close():
            if filepath in self.preview_windows:
                del self.preview_windows[filepath]
            preview_win.destroy()

        preview_win.protocol("WM_DELETE_WINDOW", on_close)

        try:
            img = Image.open(filepath)
            img.thumbnail((400, 400))
            img_tk = ImageTk.PhotoImage(img)
            label = tk.Label(preview_win, image=img_tk)
            label.image = img_tk  # keep reference
            label.pack()
        except Exception as e:
            tk.Label(preview_win, text=f"Failed to load media:\n{e}").pack()


    def setup_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True)

        # --- Messages Tab ---
        self.tab_messages = ttk.Frame(notebook)
        notebook.add(self.tab_messages, text="Messages")

        frame = ttk.Frame(self.tab_messages, padding=10)
        frame.pack(fill="both", expand=True)

        # Folder selection
        ttk.Label(frame, text="Select Folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.folder_path, width=50).grid(row=0, column=1, sticky="we")
        ttk.Button(frame, text="Browse", command=self.browse_folder).grid(row=0, column=2, padx=5)

        # Scan for DB files
        ttk.Button(frame, text="Scan for .db Files", command=self.find_databases).grid(row=1, column=1, pady=10)

        # Listbox for DB files
        self.db_listbox = tk.Listbox(frame, width=80, height=5, selectmode=tk.SINGLE)
        self.db_listbox.grid(row=2, column=0, columnspan=3, pady=10, sticky="we")

        # App preset selector
        ttk.Label(frame, text="Select App Preset:").grid(row=3, column=0, sticky="e")
        ttk.OptionMenu(frame, self.selected_app, "WhatsApp", "WhatsApp", "Messenger", "Telegram").grid(row=3, column=1, sticky="w")

        # Parse button
        ttk.Button(frame, text="Parse Selected DB", command=self.parse_selected).grid(row=4, column=1, pady=10)

        # Filters frame
        filters_frame = ttk.LabelFrame(frame, text="Filters")
        filters_frame.grid(row=5, column=0, columnspan=3, sticky="we", pady=10)

        # Search box
        ttk.Label(filters_frame, text="Search Message:").grid(row=0, column=0, sticky="e")
        ttk.Entry(filters_frame, textvariable=self.search_var, width=30).grid(row=0, column=1, padx=5, sticky="w")

        # Keyword frequency for stats
        ttk.Label(filters_frame, text="Keyword (for stats):").grid(row=0, column=2, sticky="e")
        ttk.Entry(filters_frame, textvariable=self.keyword_var, width=20).grid(row=0, column=3, padx=5, sticky="w")

        # Direction filter
        ttk.Label(filters_frame, text="Direction:").grid(row=1, column=0, sticky="e")
        ttk.OptionMenu(filters_frame, self.direction_var, "All", "All", "Sent", "Received").grid(row=1, column=1, sticky="w")

        # Date range filter
        ttk.Label(filters_frame, text="Start Date (YYYY-MM-DD):").grid(row=1, column=2, sticky="e")
        ttk.Entry(filters_frame, textvariable=self.start_date_var, width=15).grid(row=1, column=3, padx=5, sticky="w")
        ttk.Label(filters_frame, text="End Date (YYYY-MM-DD):").grid(row=2, column=2, sticky="e")
        ttk.Entry(filters_frame, textvariable=self.end_date_var, width=15).grid(row=2, column=3, padx=5, sticky="w")

        # Contact filter label and Listbox
        ttk.Label(filters_frame, text="Filter by Contact(s):").grid(row=2, column=0, sticky="ne")
        self.contact_listbox = tk.Listbox(filters_frame, selectmode=tk.MULTIPLE, height=5, exportselection=False)
        self.contact_listbox.grid(row=2, column=1, sticky="we", padx=5, pady=5)
        filters_frame.columnconfigure(1, weight=1)

        # Filter buttons
        btn_frame = ttk.Frame(filters_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10)

        ttk.Button(btn_frame, text="Apply Filters", command=self.apply_filters).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Filters", command=self.clear_filters).pack(side="left", padx=5)

        # Treeview for messages
        columns = ("Contact", "Message", "Timestamp", "Direction")
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)
        self.tree.grid(row=6, column=0, columnspan=3, pady=10, sticky="nsew")

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=6, column=3, sticky='ns')

        # Configure grid weights
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, weight=1)

        # --- Stats Tab ---
        self.tab_stats = ttk.Frame(notebook)
        notebook.add(self.tab_stats, text="Stats")

        # --- Media Tab ---
        self.tab_media = ttk.Frame(notebook)
        notebook.add(self.tab_media, text="Media")

        # Media Treeview
        media_columns = ("Contact", "Timestamp", "Media Path", "Media Type", "Media Mime")
        self.media_tree = ttk.Treeview(self.tab_media, columns=media_columns, show='headings', height=15)
        for col in media_columns:
            self.media_tree.heading(col, text=col)
            self.media_tree.column(col, width=180)
        self.media_tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Media preview on double-click
        self.media_tree.bind("<Double-1>", self.on_media_select)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)

    def find_databases(self):
        self.db_listbox.delete(0, tk.END)
        folder = self.folder_path.get()
        dbs = find_sqlite_files(folder)
        for db in dbs:
            self.db_listbox.insert(tk.END, db)

    def parse_selected(self):
        try:
            selected = self.db_listbox.get(self.db_listbox.curselection())
            self.df = parse_db(selected, self.selected_app.get())

            # Fill contacts listbox for filtering
            self.contact_listbox.delete(0, tk.END)
            contacts = sorted(self.df['Contact'].dropna().unique())
            for c in contacts:
                self.contact_listbox.insert(tk.END, c)

            self.apply_filters()
            self.update_media_tab()  # <-- Add this line!
            messagebox.showinfo("Success", "Parsed and loaded data from the selected database.")
        except Exception as e:
            messagebox.showerror("Error", f"Error parsing DB: {e}")

    def apply_filters(self):
        if self.df is None:
            return

        df_filtered = self.df.copy()

        # Search message text
        search_text = self.search_var.get().lower()
        if search_text:
            df_filtered = df_filtered[df_filtered['Message'].str.lower().str.contains(search_text, na=False)]

        # Keyword frequency for stats (store keyword)
        self.keyword = self.keyword_var.get().lower()

        # Direction filter
        direction = self.direction_var.get()
        if direction != "All":
            df_filtered = df_filtered[df_filtered['Direction'] == direction]

        # Date range filter
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()
        try:
            if start_date:
                start_dt = pd.to_datetime(start_date)
                df_filtered = df_filtered[df_filtered['timestamp'] >= start_dt]
            if end_date:
                end_dt = pd.to_datetime(end_date)
                df_filtered = df_filtered[df_filtered['timestamp'] <= end_dt]
        except Exception:
            messagebox.showwarning("Date format error", "Please enter dates in YYYY-MM-DD format.")

        # Contact filter
        selected_indices = self.contact_listbox.curselection()
        if selected_indices:
            selected_contacts = [self.contact_listbox.get(i) for i in selected_indices]
            df_filtered = df_filtered[df_filtered['Contact'].isin(selected_contacts)]

        self.filtered_df = df_filtered

        # Update message list
        self.update_message_table()

        # Update stats tab
        self.update_stats_tab()

        # Update media tab with filtered data
        self.update_media_tab()  # <-- Add this line!

    def clear_filters(self):
        self.search_var.set("")
        self.keyword_var.set("")
        self.direction_var.set("All")
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.contact_listbox.selection_clear(0, tk.END)
        self.apply_filters()

    def update_message_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for _, row in self.filtered_df.iterrows():
            self.tree.insert("", "end", values=(
                row.get('Contact', ''),
                row.get('Message', ''),
                row.get('timestamp', ''),
                row.get('Direction', '')
            ))

    def update_stats_tab(self):
        # Clear previous widgets
        for widget in self.tab_stats.winfo_children():
            widget.destroy()

        if self.filtered_df is None or self.filtered_df.empty:
            ttk.Label(self.tab_stats, text="No data to show stats for.").pack(pady=10)
            return

        # Total messages count
        total_msgs = len(self.filtered_df)

        # Sent vs Received counts
        sent_count = (self.filtered_df['Direction'] == 'Sent').sum()
        received_count = (self.filtered_df['Direction'] == 'Received').sum()

        # Messages per day
        daily_counts = self.filtered_df.copy()
        daily_counts['date_only'] = pd.to_datetime(daily_counts['timestamp']).dt.date
        counts_per_day = daily_counts.groupby('date_only').size()

        # Keyword frequency count if keyword provided
        keyword_count = 0
        if self.keyword:
            keyword_count = self.filtered_df['Message'].dropna().str.lower().str.count(re.escape(self.keyword)).sum()

        # Display stats
        ttk.Label(self.tab_stats, text="Statistics Summary", font=('Helvetica', 16, 'bold')).pack(anchor='w', pady=10)

        ttk.Label(self.tab_stats, text=f"Total Messages: {total_msgs}").pack(anchor='w', padx=20)
        ttk.Label(self.tab_stats, text=f"Sent Messages: {sent_count}").pack(anchor='w', padx=20)
        ttk.Label(self.tab_stats, text=f"Received Messages: {received_count}").pack(anchor='w', padx=20)

        if self.keyword:
            ttk.Label(self.tab_stats, text=f"Occurrences of keyword '{self.keyword}': {keyword_count}").pack(anchor='w', padx=20, pady=(5, 10))

        ttk.Label(self.tab_stats, text="Messages per Day:").pack(anchor='w', pady=(10, 0), padx=20)

        # Messages per day text box
        text_box = tk.Text(self.tab_stats, height=10, width=40)
        text_box.pack(padx=20, pady=5)
        for date, count in counts_per_day.items():
            text_box.insert(tk.END, f"{date}: {count}\n")
        text_box.config(state=tk.DISABLED)

    def on_media_select(self, event):
        selected = self.media_tree.selection()
        if not selected or self.df is None:
            return
        index = self.media_tree.index(selected[0])
        row = self.media_df.iloc[index]
        media_path = row.get("media_path")
        if media_path and os.path.isfile(media_path):
            self.show_media_preview(media_path)

    def update_media_tab(self):
        # Use filtered_df instead of df for consistency with filters
        if self.filtered_df is None:
            self.media_df = pd.DataFrame()
        else:
            self.filtered_df['media_path'] = self.filtered_df['media_path'].astype(str).str.strip()
            self.media_df = self.filtered_df[self.filtered_df['media_path'].notnull() & (self.filtered_df['media_path'] != '')].copy()

        for row in self.media_tree.get_children():
            self.media_tree.delete(row)

        for _, row in self.media_df.iterrows():
            self.media_tree.insert("", "end", values=(
                row.get('Contact', ''),
                row.get('timestamp', ''),
                row.get('media_path', ''),
                row.get('media_type', ''),
                row.get('media_mime', '')
            ))

        # Clear previous summary widgets
        for widget in getattr(self, 'media_summary_widgets', []):
            widget.destroy()
        self.media_summary_widgets = []

        # Media count per contact
        if not self.media_df.empty:
            counts = self.media_df['Contact'].value_counts()
            summary = "Media count per contact:\n"
            for contact, count in counts.items():
                summary += f"{contact}: {count}\n"
        else:
            summary = "No media found for current filter."

        label = tk.Label(self.tab_media, text=summary, justify="left", anchor="w")
        label.pack(anchor="nw", padx=10, pady=(5, 0))
        self.media_summary_widgets = [label]

        # Prioritize selected contacts at the top
        selected_indices = self.contact_listbox.curselection()
        if selected_indices:
            selected_contacts = [self.contact_listbox.get(i) for i in selected_indices]
            self.media_df['priority'] = self.media_df['Contact'].apply(lambda c: 0 if c in selected_contacts else 1)
            self.media_df = self.media_df.sort_values(['priority', 'Contact', 'timestamp'])
            self.media_df = self.media_df.drop(columns=['priority'])
        else:
            self.media_df = self.media_df.sort_values(['Contact', 'timestamp'])

def run_app():
    root = tk.Tk()

    # Load icon from ParsePal/icon.png relative to current working dir
    icon_path = os.path.join(os.getcwd(), "icon.png")
    print(f"Loading icon from: {icon_path}")
    try:
        icon_img = tk.PhotoImage(file=icon_path)
        root.iconphoto(False, icon_img)
        print("Icon loaded successfully")
    except Exception as e:
        print(f"Failed to load icon: {e}")

    app = ParsePalApp(root)
    root.mainloop()
