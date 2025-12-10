#!/usr/bin/env python3
"""
Video/Audio Transcription Tool with Tkinter GUI
Converts video/audio files to timestamped transcripts using Whisper
Supports multiple formats: .ts, .mp4, .mkv, .wav, .mp3, .m4a, etc.
Author: AI Assistant
Features:
  - Single or batch file transcription
  - Support for 15+ video/audio formats
  - Configurable Whisper model and language
  - Multiple output formats (txt, srt, vtt, json, tsv)
  - Real-time transcription log with all Whisper output
  - Modern responsive Tkinter GUI
"""

import os
import sys
import threading
import subprocess
import json
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


class TranscriptionConfig:
    """Configuration for transcription settings"""
    SUPPORTED_FORMATS = {
        'Video': ['.ts', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm'],
        'Audio': ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma'],
        'All': ['.ts', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm',
                '.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma']
    }
    
    WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large']
    DEFAULT_MODEL = 'small'
    DEFAULT_LANGUAGE = 'en'
    LANGUAGES = ['en', 'te', 'es', 'fr', 'de', 'ja', 'zh', 'pt', 'ru', 'ar', 'hi']
    OUTPUT_FORMATS = ['txt', 'srt', 'vtt', 'json', 'tsv']


class TranscriptionEngine:
    """Handles transcription using Whisper"""
    
    def __init__(self, model='small', language='en'):
        self.model = model
        self.language = language
        self.is_running = False
    
    def transcribe_file(self, file_path, output_dir, output_format='txt', callback=None):
        """
        Transcribe a single file
        Args:
            file_path: Path to media file
            output_dir: Output directory
            output_format: Format for output
            callback: Function to call with status updates
        """
        try:
            file_path = Path(file_path)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if callback:
                callback(f"\n{'='*80}\n📍 Processing: {file_path.name}\n{'='*80}")
            
            # Build whisper command
            cmd = [
                'whisper',
                str(file_path),
                '--model', self.model,
                '--language', self.language,
                '--task', 'transcribe',
                '--output_format', output_format,
                '--output_dir', str(output_dir)
            ]
            
            if callback:
                callback(f"\n$ {' '.join(cmd)}\n")
            
            # Run whisper with real-time output capture
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                bufsize=1
            )
            
            # Capture all output line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    if callback:
                        callback(line.rstrip())
            
            process.wait()
            
            if process.returncode == 0:
                output_file = output_dir / f"{file_path.stem}.{output_format}"
                if callback:
                    callback(f"\n✅ SUCCESS: {file_path.name}")
                    callback(f"📄 Output: {output_file.name}\n")
                return True, str(output_file)
            else:
                if callback:
                    callback(f"\n❌ FAILED: {file_path.name}\n")
                return False, "Transcription failed"
        
        except Exception as e:
            if callback:
                callback(f"\n❌ ERROR in {file_path.name}: {str(e)}\n")
            return False, str(e)
    
    def transcribe_batch(self, file_list, output_dir, output_format='txt', callback=None):
        """Transcribe multiple files"""
        results = []
        total = len(file_list)
        
        for idx, file_path in enumerate(file_list, 1):
            if not self.is_running:
                if callback:
                    callback("\n⏹️  STOPPED by user\n")
                break
            
            if callback:
                callback(f"\n{'#'*80}\n[{idx}/{total}] Processing: {Path(file_path).name}\n{'#'*80}")
            
            success, result = self.transcribe_file(file_path, output_dir, output_format, callback)
            results.append({
                'file': str(file_path),
                'success': success,
                'result': result
            })
        
        return results
    
    def stop(self):
        """Stop transcription"""
        self.is_running = False


class TranscriptionGUI:
    """Main GUI Application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Transcription Studio")
        self.root.geometry("1200x700")
        self.root.resizable(True, True)
        
        self.engine = None
        self.worker_thread = None
        self.selected_files = []
        self.output_directory = Path.home() / "Transcriptions"
        self.is_transcribing = False
        
        self.setup_styles()
        self.create_widgets()
        self.setup_grid_weights()
    
    def setup_styles(self):
        """Configure ttk styles with modern colors"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern color palette
        bg_primary = '#1e1e2e'    # Dark background
        bg_secondary = '#2a2a3e'  # Slightly lighter
        fg_primary = '#e0e0e0'    # Light text
        fg_secondary = '#a0a0a0'  # Dimmed text
        accent = '#00d9ff'        # Cyan accent
        success = '#00ff88'       # Green
        warning = '#ffaa00'       # Orange
        
        style.configure('TFrame', background=bg_primary)
        style.configure('TLabel', background=bg_primary, foreground=fg_primary)
        style.configure('TButton', background=bg_secondary, foreground=fg_primary)
        style.configure('TLabelframe', background=bg_primary, foreground=fg_primary)
        style.configure('TLabelframe.Label', background=bg_primary, foreground=accent)
        style.configure('Header.TLabel', font=('Arial', 11, 'bold'), foreground=accent)
        style.configure('Info.TLabel', font=('Arial', 9), foreground=fg_secondary)
        style.configure('Success.TLabel', foreground=success)
        style.configure('Warning.TLabel', foreground=warning)
        
        # Configure root background
        self.root.configure(bg=bg_primary)
    
    def create_widgets(self):
        """Create all GUI widgets with side-by-side layout"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        
        # LEFT SIDE: File Selection
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        files_frame = ttk.LabelFrame(left_frame, text="📁 File Selection", padding=10)
        files_frame.pack(fill='both', expand=True, pady=(0, 10))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(2, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(files_frame)
        button_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        ttk.Button(button_frame, text="📂 Folder", command=self.select_folder, width=12).pack(side='left', padx=2)
        ttk.Button(button_frame, text="📄 Files", command=self.select_files, width=12).pack(side='left', padx=2)
        ttk.Button(button_frame, text="🗑️ Clear", command=self.clear_selection, width=12).pack(side='left', padx=2)
        
        # File count
        ttk.Label(files_frame, text="Selected Files:", style='Header.TLabel').grid(row=1, column=0, sticky='w')
        self.file_count_label = ttk.Label(files_frame, text="0 files", style='Info.TLabel')
        self.file_count_label.grid(row=1, column=0, sticky='e')
        
        # File list
        list_frame = ttk.Frame(files_frame)
        list_frame.grid(row=2, column=0, sticky='nsew')
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.file_listbox = tk.Listbox(list_frame, height=15, yscrollcommand=scrollbar.set, 
                                       font=('Courier', 9), bg='#2a2a3e', fg='#e0e0e0')
        self.file_listbox.pack(side='left', fill='both', expand=True)
        self.file_listbox.bind('<Double-Button-1>', self.remove_selected_file)
        scrollbar.config(command=self.file_listbox.yview)
        
        ttk.Label(files_frame, text="Double-click to remove", style='Info.TLabel').grid(row=3, column=0, sticky='w', pady=(5, 0))
        
        # RIGHT SIDE: Settings
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        settings_frame = ttk.LabelFrame(right_frame, text="⚙️ Settings", padding=15)
        settings_frame.pack(fill='x', pady=(0, 10))
        
        # Model
        ttk.Label(settings_frame, text="Model:", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=10)
        self.model_var = tk.StringVar(value=TranscriptionConfig.DEFAULT_MODEL)
        model_combo = ttk.Combobox(settings_frame, textvariable=self.model_var,
                                   values=TranscriptionConfig.WHISPER_MODELS, state='readonly', width=15)
        model_combo.grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        ttk.Label(settings_frame, text="tiny=fast | large=accurate", style='Info.TLabel').grid(row=0, column=2, sticky='w')
        
        # Language
        ttk.Label(settings_frame, text="Language:", style='Header.TLabel').grid(row=1, column=0, sticky='w', pady=10)
        self.language_var = tk.StringVar(value=TranscriptionConfig.DEFAULT_LANGUAGE)
        lang_combo = ttk.Combobox(settings_frame, textvariable=self.language_var,
                                  values=TranscriptionConfig.LANGUAGES, state='readonly', width=15)
        lang_combo.grid(row=1, column=1, sticky='ew', padx=10, pady=10)
        ttk.Label(settings_frame, text="en=English | te=Telugu", style='Info.TLabel').grid(row=1, column=2, sticky='w')
        
        # Format
        ttk.Label(settings_frame, text="Format:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=10)
        self.format_var = tk.StringVar(value='txt')
        format_combo = ttk.Combobox(settings_frame, textvariable=self.format_var,
                                    values=TranscriptionConfig.OUTPUT_FORMATS, state='readonly', width=15)
        format_combo.grid(row=2, column=1, sticky='ew', padx=10, pady=10)
        ttk.Label(settings_frame, text="txt=text | srt=subtitles", style='Info.TLabel').grid(row=2, column=2, sticky='w')
        
        # Output Directory
        ttk.Label(settings_frame, text="Output:", style='Header.TLabel').grid(row=3, column=0, sticky='nw', pady=10)
        output_frame = ttk.Frame(settings_frame)
        output_frame.grid(row=3, column=1, columnspan=2, sticky='ew', padx=10, pady=10)
        output_frame.columnconfigure(0, weight=1)
        
        self.output_path_label = ttk.Label(output_frame, text=self.output_directory.name, style='Info.TLabel')
        self.output_path_label.pack(side='left', fill='x', expand=True)
        ttk.Button(output_frame, text="Change", command=self.select_output_dir, width=8).pack(side='left', padx=5)
        
        # Separator
        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Action Buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill='x')
        
        self.start_btn = ttk.Button(button_frame, text="▶️  START", command=self.start_transcription, width=18)
        self.start_btn.pack(pady=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹️  STOP", command=self.stop_transcription, width=18, state='disabled')
        self.stop_btn.pack(pady=5)
        
        ttk.Button(button_frame, text="📂 Open Folder", command=self.open_output_folder, width=18).pack(pady=5)
        
        # Status
        status_frame = ttk.LabelFrame(right_frame, text="📊 Status", padding=10)
        status_frame.pack(fill='x', pady=10)
        
        self.status_label = ttk.Label(status_frame, text="Ready", style='Success.TLabel', font=('Arial', 10, 'bold'))
        self.status_label.pack(anchor='w')
        
        # BOTTOM: Log
        log_frame = ttk.LabelFrame(main_frame, text="📝 Processing Log", padding=10)
        log_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=('Courier', 9),
                                                   wrap='word', bg='#2a2a3e', fg='#00ff88')
        self.log_text.pack(fill='both', expand=True)
        
        # Grid configuration
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=2)
        main_frame.rowconfigure(1, weight=1)
    
    def setup_grid_weights(self):
        """Configure grid weights"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def remove_selected_file(self, event):
        """Remove selected file from list"""
        selection = self.file_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.selected_files[idx]
            self.update_file_list()
    
    def select_folder(self):
        """Select a folder with media files"""
        folder = filedialog.askdirectory(title="Select Folder with Media Files")
        if folder:
            self.load_files_from_folder(folder)
    
    def select_files(self):
        """Select individual media files"""
        file_types = [
            ("Video Files", " ".join([f"*{ext}" for ext in TranscriptionConfig.SUPPORTED_FORMATS['Video']])),
            ("Audio Files", " ".join([f"*{ext}" for ext in TranscriptionConfig.SUPPORTED_FORMATS['Audio']])),
            ("All Supported", " ".join([f"*{ext}" for ext in TranscriptionConfig.SUPPORTED_FORMATS['All']])),
            ("All Files", "*.*")
        ]
        
        files = filedialog.askopenfilenames(title="Select Media Files", filetypes=file_types)
        
        if files:
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
            self.update_file_list()
    
    def select_output_dir(self):
        """Select output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_directory = Path(directory)
            self.output_path_label.config(text=self.output_directory.name)
            self.log(f"📂 Output: {self.output_directory}")
    
    def load_files_from_folder(self, folder):
        """Load all supported media files from folder"""
        folder_path = Path(folder)
        supported_extensions = TranscriptionConfig.SUPPORTED_FORMATS['All']
        
        files = []
        for ext in supported_extensions:
            files.extend(folder_path.glob(f"*{ext}"))
            files.extend(folder_path.glob(f"*{ext.upper()}"))
        
        if files:
            files = sorted(set([str(f) for f in files]))
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.update_file_list()
            self.log(f"✅ Loaded {len(files)} file(s) from '{folder_path.name}'")
        else:
            messagebox.showwarning("No Files", f"No media files found in:\n{folder_path}")
    
    def update_file_list(self):
        """Update the file listbox display"""
        self.file_listbox.delete(0, tk.END)
        for file in self.selected_files:
            filename = Path(file).name
            self.file_listbox.insert(tk.END, filename)
        
        count = len(self.selected_files)
        self.file_count_label.config(text=f"{count} file{'s' if count != 1 else ''}")
    
    def clear_selection(self):
        """Clear selected files"""
        self.selected_files = []
        self.update_file_list()
        self.log("🗑️  All files cleared")
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_progress(self, callback_message):
        """Update progress from transcription callback"""
        self.log(callback_message)
    
    def start_transcription(self):
        """Start transcription process"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select at least one file to transcribe.")
            return
        
        # Update button states
        self.is_transcribing = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_label.config(text="⏳ Processing...", foreground='#ffaa00')
        
        self.log_text.delete(1.0, tk.END)  # Clear log
        self.log(f"{'='*90}")
        self.log(f"🚀 STARTING TRANSCRIPTION")
        self.log(f"{'='*90}")
        self.log(f"📊 Files: {len(self.selected_files)} | Model: {self.model_var.get()} | Language: {self.language_var.get()}")
        self.log(f"📄 Format: {self.format_var.get()} | Output: {self.output_directory.name}")
        self.log(f"{'='*90}\n")
        
        self.engine = TranscriptionEngine(
            model=self.model_var.get(),
            language=self.language_var.get()
        )
        self.engine.is_running = True
        
        self.worker_thread = threading.Thread(target=self.transcription_worker, daemon=True)
        self.worker_thread.start()
    
    def transcription_worker(self):
        """Worker thread for transcription"""
        try:
            results = self.engine.transcribe_batch(
                self.selected_files,
                self.output_directory,
                self.format_var.get(),
                callback=self.update_progress
            )
            
            # Summary
            success_count = sum(1 for r in results if r['success'])
            total_count = len(results)
            
            self.log(f"\n{'='*90}")
            self.log(f"✅ COMPLETE: {success_count}/{total_count} successful")
            self.log(f"{'='*90}\n")
            
            # Update UI
            if success_count == total_count:
                self.status_label.config(text="✅ All files transcribed!", foreground='#00ff88')
                self.root.after(0, lambda: messagebox.showinfo("Success", 
                    f"All {success_count} file(s) transcribed!\n\nOutput: {self.output_directory}"))
            else:
                self.status_label.config(text=f"⚠️  {success_count}/{total_count} successful", foreground='#ffaa00')
                self.root.after(0, lambda: messagebox.showwarning("Partial Success",
                    f"{success_count}/{total_count} files completed.\nCheck log for errors."))
        
        except Exception as e:
            self.log(f"\n❌ FATAL ERROR: {str(e)}\n")
            self.status_label.config(text="❌ Error occurred", foreground='#ff4444')
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed:\n{str(e)}"))
        
        finally:
            # Reset button states
            self.is_transcribing = False
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
    
    def stop_transcription(self):
        """Stop transcription"""
        if self.engine and self.is_transcribing:
            self.engine.stop()
            self.status_label.config(text="⏹️  Stopped by user", foreground='#ffaa00')
    
    def open_output_folder(self):
        """Open output folder in file explorer"""
        if self.output_directory.exists():
            try:
                if sys.platform == 'win32':
                    os.startfile(str(self.output_directory))
                elif sys.platform == 'darwin':
                    os.system(f'open "{self.output_directory}"')
                else:
                    os.system(f'xdg-open "{self.output_directory}"')
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder:\n{str(e)}")
        else:
            messagebox.showwarning("Not Found", f"Folder does not exist:\n{self.output_directory}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TranscriptionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()