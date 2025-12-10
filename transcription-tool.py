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
  - Real-time transcription log
  - Fully responsive Tkinter GUI
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
            self.is_running = True
            file_path = Path(file_path)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if callback:
                callback(f"Starting transcription: {file_path.name}")
            
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
            
            # Run whisper
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=None
            )
            
            if result.returncode == 0:
                output_file = output_dir / f"{file_path.stem}.{output_format}"
                if callback:
                    callback(f"✓ Completed: {file_path.name}\nOutput: {output_file}")
                return True, str(output_file)
            else:
                error = result.stderr or "Unknown error"
                if callback:
                    callback(f"✗ Error transcribing {file_path.name}: {error}")
                return False, error
        
        except subprocess.TimeoutExpired:
            if callback:
                callback(f"✗ Timeout: Transcription took too long for {file_path.name}")
            return False, "Timeout"
        except Exception as e:
            if callback:
                callback(f"✗ Exception: {str(e)}")
            return False, str(e)
        finally:
            self.is_running = False
    
    def transcribe_batch(self, file_list, output_dir, output_format='txt', callback=None):
        """Transcribe multiple files"""
        results = []
        total = len(file_list)
        
        for idx, file_path in enumerate(file_list, 1):
            if not self.is_running:
                break
            
            if callback:
                callback(f"Processing {idx}/{total}: {Path(file_path).name}")
            
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
        self.root.title("Video/Audio Transcription Tool")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        
        self.engine = None
        self.worker_thread = None
        self.selected_files = []
        self.output_directory = Path.home() / "Transcriptions"
        
        self.setup_styles()
        self.create_widgets()
        self.setup_grid_weights()
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Define colors
        bg_color = '#f0f0f0'
        fg_color = '#333333'
        accent_color = '#2196F3'
        
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TButton', background=bg_color)
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground=accent_color)
        style.configure('Info.TLabel', font=('Arial', 9), foreground='#666666')
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        
        # ===== INPUT SECTION =====
        input_frame = ttk.LabelFrame(main_frame, text="Input Configuration", padding=10)
        input_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        
        # File/Folder Selection
        ttk.Label(input_frame, text="Select Input:", style='Header.TLabel').grid(row=0, column=0, sticky='w')
        
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=0, column=1, sticky='ew', padx=(10, 0))
        
        ttk.Button(button_frame, text="📁 Select Folder", command=self.select_folder).pack(side='left', padx=2)
        ttk.Button(button_frame, text="📄 Select File(s)", command=self.select_files).pack(side='left', padx=2)
        ttk.Button(button_frame, text="🗑️ Clear", command=self.clear_selection).pack(side='left', padx=2)
        
        # File list display
        ttk.Label(input_frame, text="Selected Files:", style='Header.TLabel').grid(row=1, column=0, sticky='nw', pady=(10, 0))
        
        list_frame = ttk.Frame(input_frame)
        list_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', pady=(5, 0))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.file_listbox = tk.Listbox(list_frame, height=6, yscrollcommand=scrollbar.set, font=('Arial', 9))
        self.file_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # ===== SETTINGS SECTION =====
        settings_frame = ttk.LabelFrame(main_frame, text="Transcription Settings", padding=10)
        settings_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        
        # Model Selection
        ttk.Label(settings_frame, text="Whisper Model:", style='Header.TLabel').grid(row=0, column=0, sticky='w')
        self.model_var = tk.StringVar(value=TranscriptionConfig.DEFAULT_MODEL)
        model_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.model_var,
            values=TranscriptionConfig.WHISPER_MODELS,
            state='readonly',
            width=15
        )
        model_combo.grid(row=0, column=1, sticky='w', padx=(10, 0))
        ttk.Label(settings_frame, text="(tiny=fast, large=accurate)", style='Info.TLabel').grid(row=0, column=2, sticky='w', padx=10)
        
        # Language Selection
        ttk.Label(settings_frame, text="Language:", style='Header.TLabel').grid(row=1, column=0, sticky='w', pady=(10, 0))
        self.language_var = tk.StringVar(value=TranscriptionConfig.DEFAULT_LANGUAGE)
        language_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.language_var,
            values=['en', 'es', 'fr', 'de', 'ja', 'zh'],
            state='readonly',
            width=15
        )
        language_combo.grid(row=1, column=1, sticky='w', padx=(10, 0), pady=(10, 0))
        ttk.Label(settings_frame, text="(English, Spanish, French, etc.)", style='Info.TLabel').grid(row=1, column=2, sticky='w', padx=10, pady=(10, 0))
        
        # Output Format
        ttk.Label(settings_frame, text="Output Format:", style='Header.TLabel').grid(row=2, column=0, sticky='w', pady=(10, 0))
        self.format_var = tk.StringVar(value='txt')
        format_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.format_var,
            values=TranscriptionConfig.OUTPUT_FORMATS,
            state='readonly',
            width=15
        )
        format_combo.grid(row=2, column=1, sticky='w', padx=(10, 0), pady=(10, 0))
        ttk.Label(settings_frame, text="(txt, srt, vtt, json, tsv)", style='Info.TLabel').grid(row=2, column=2, sticky='w', padx=10, pady=(10, 0))
        
        # Output Directory
        ttk.Label(settings_frame, text="Output Directory:", style='Header.TLabel').grid(row=3, column=0, sticky='w', pady=(10, 0))
        output_button_frame = ttk.Frame(settings_frame)
        output_button_frame.grid(row=3, column=1, columnspan=2, sticky='ew', padx=(10, 0), pady=(10, 0))
        
        self.output_path_label = ttk.Label(output_button_frame, text=str(self.output_directory), style='Info.TLabel', foreground='#1976D2')
        self.output_path_label.pack(side='left')
        ttk.Button(output_button_frame, text="Browse", command=self.select_output_dir).pack(side='left', padx=10)
        
        # ===== ACTION SECTION =====
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        
        ttk.Button(action_frame, text="▶️  Start Transcription", command=self.start_transcription).pack(side='left', padx=5)
        ttk.Button(action_frame, text="⏹️  Stop", command=self.stop_transcription).pack(side='left', padx=5)
        ttk.Button(action_frame, text="📂 Open Output Folder", command=self.open_output_folder).pack(side='left', padx=5)
        
        # ===== PROGRESS SECTION =====
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding=10)
        progress_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
        self.status_label = ttk.Label(progress_frame, text="Ready", style='Info.TLabel')
        self.status_label.pack(anchor='w')
        
        # ===== LOG SECTION =====
        log_frame = ttk.LabelFrame(main_frame, text="Transcription Log", padding=10)
        log_frame.grid(row=4, column=0, columnspan=2, sticky='nsew', pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            font=('Courier', 9),
            wrap='word'
        )
        self.log_text.pack(fill='both', expand=True)
        
        input_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
    
    def setup_grid_weights(self):
        """Configure grid weights for responsiveness"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def select_folder(self):
        """Select a folder with media files"""
        folder = filedialog.askdirectory(title="Select Folder with Media Files")
        if folder:
            self.load_files_from_folder(folder)
    
    def select_files(self):
        """Select individual media files"""
        file_types = (
            ("All Supported", "*" + "*".join(TranscriptionConfig.SUPPORTED_FORMATS['All'])),
            ("Video Files", "*" + "*".join(TranscriptionConfig.SUPPORTED_FORMATS['Video'])),
            ("Audio Files", "*" + "*".join(TranscriptionConfig.SUPPORTED_FORMATS['Audio'])),
            ("All Files", "*.*")
        )
        
        files = filedialog.askopenfilenames(
            title="Select Media Files",
            filetypes=file_types
        )
        
        if files:
            self.selected_files.extend(files)
            self.update_file_list()
    
    def select_output_dir(self):
        """Select output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_directory = Path(directory)
            self.output_path_label.config(text=str(self.output_directory))
    
    def load_files_from_folder(self, folder):
        """Load all supported media files from folder"""
        folder_path = Path(folder)
        supported_extensions = TranscriptionConfig.SUPPORTED_FORMATS['All']
        
        files = []
        for ext in supported_extensions:
            files.extend(folder_path.glob(f"*{ext}"))
            files.extend(folder_path.glob(f"*{ext.upper()}"))
        
        if files:
            self.selected_files = sorted(set([str(f) for f in files]))
            self.update_file_list()
            self.log(f"Loaded {len(self.selected_files)} media file(s) from {folder_path.name}")
        else:
            messagebox.showwarning("No Files", "No supported media files found in the selected folder.")
    
    def update_file_list(self):
        """Update the file listbox display"""
        self.file_listbox.delete(0, tk.END)
        for file in self.selected_files:
            self.file_listbox.insert(tk.END, Path(file).name)
    
    def clear_selection(self):
        """Clear selected files"""
        self.selected_files = []
        self.update_file_list()
        self.log("Selection cleared")
    
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
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
        
        self.log("=" * 60)
        self.log(f"Starting batch transcription at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Files: {len(self.selected_files)}, Model: {self.model_var.get()}, Language: {self.language_var.get()}")
        self.log("=" * 60)
        
        self.engine = TranscriptionEngine(
            model=self.model_var.get(),
            language=self.language_var.get()
        )
        
        self.worker_thread = threading.Thread(
            target=self.transcription_worker,
            daemon=True
        )
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
            self.log("=" * 60)
            success_count = sum(1 for r in results if r['success'])
            self.log(f"Transcription Complete: {success_count}/{len(results)} successful")
            self.log("=" * 60)
            
            if success_count == len(results):
                self.root.after(0, lambda: messagebox.showinfo("Success", f"All {success_count} file(s) transcribed successfully!"))
            else:
                self.root.after(0, lambda: messagebox.showwarning("Partial Success", f"{success_count}/{len(results)} files transcribed successfully."))
        
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Transcription failed: {str(e)}"))
    
    def stop_transcription(self):
        """Stop transcription"""
        if self.engine:
            self.engine.stop()
            self.log("Transcription stopped by user")
    
    def open_output_folder(self):
        """Open output folder in file explorer"""
        if self.output_directory.exists():
            if sys.platform == 'win32':
                os.startfile(str(self.output_directory))
            elif sys.platform == 'darwin':
                os.system(f'open "{self.output_directory}"')
            else:
                os.system(f'xdg-open "{self.output_directory}"')
        else:
            messagebox.showwarning("Folder Not Found", "Output folder does not exist yet.")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TranscriptionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
