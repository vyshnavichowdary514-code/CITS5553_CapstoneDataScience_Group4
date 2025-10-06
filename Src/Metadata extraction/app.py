import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image
from pathlib import Path
import xml.etree.ElementTree as ET
import json
import re
import os
from sem_meta import SEMMeta

# ------------------ Helper Functions ------------------

def strip_ns_key(key):
    return key.split('}')[-1] if '}' in key else key

def xml_to_dict(elem):
    children = list(elem)
    if not children:
        text = elem.text.strip() if elem.text and elem.text.strip() else None
        return text
    result = {}
    for child in children:
        child_dict = xml_to_dict(child)
        tag = strip_ns_key(child.tag)
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(child_dict)
        else:
            result[tag] = child_dict
    return result

def strip_ns(d):
    if isinstance(d, dict):
        return {strip_ns_key(k): strip_ns(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [strip_ns(i) for i in d]
    else:
        return d

def parse_value(value):
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        return [parse_value(v) for v in value]
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            return None
    if isinstance(value, str):
        try:
            root = ET.fromstring(value)
            return {strip_ns_key(root.tag): xml_to_dict(root)}
        except ET.ParseError:
            pass
        if "=" in value:
            kv = {}
            for line in value.splitlines():
                if "=" in line:
                    key, val = line.split("=", 1)
                    kv[key.strip()] = val.strip()
            if kv:
                return {"plain": kv}
    try:
        json.dumps(value)
        return value
    except Exception:
        return None

def convert_meta_to_json(meta):
    clean_meta = {}
    for k, v in meta.items():
        try:
            parsed_value = parse_value(v)
            clean_meta[str(k)] = strip_ns(parsed_value)
        except Exception:
            clean_meta[str(k)] = None
    return clean_meta

def parse_jeol_metadata(meta_path):
    data = {}
    try:
        with open(meta_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("$"):
                    match = re.match(r"^\$+([A-Z0-9_%]+)\s*(.*)$", line)
                    if match:
                        key, val = match.groups()
                        data[key.strip()] = val.strip()
    except Exception as e:
        data = {"Error": f"Failed to parse metadata: {e}"}
    return data

# ------------------ Extraction Logic ------------------

def extract_from_image(image_path):
    with Image.open(image_path) as im:
        meta, tags = SEMMeta.ImageMetadata(im)
        json_meta = convert_meta_to_json(meta)
        return {"image": Path(image_path).name, "metadata": json_meta}

def extract_from_image_and_text(image_path, meta_path):
    meta_data = parse_jeol_metadata(meta_path)
    base_name = Path(image_path).stem
    machine_name = meta_data.get("CM_INSTRUMENT", "Unknown").strip()
    date_taken = meta_data.get("CM_DATE", "Unknown").replace("/", "-")
    unified_name = f"{base_name}_{machine_name}_{date_taken}"
    return {
        "id": base_name,
        "image_file": f"{unified_name}.tif",
        "metadata_file": f"{unified_name}.txt",
        "machine": machine_name,
        "date_taken": date_taken,
        "metadata": meta_data
    }

# ------------------ GUI Functions ------------------

def select_image():
    global image_path
    image_path = filedialog.askopenfilename(
        title="Select SEM Image",
        filetypes=[("SEM Images", "*.tif *.tiff *.bmp *.jpg *.jpeg *.png")]
    )
    if image_path:
        entry_image.config(state="normal")
        entry_image.delete(0, tk.END)
        entry_image.insert(0, str(Path(image_path)))
        entry_image.config(state="readonly")

def select_metadata():
    global meta_path
    meta_path = filedialog.askopenfilename(
        title="Select Metadata File (Optional)",
        filetypes=[("Text files", "*.txt")]
    )
    if meta_path:
        entry_meta.config(state="normal")
        entry_meta.delete(0, tk.END)
        entry_meta.insert(0, str(Path(meta_path)))
        entry_meta.config(state="readonly")

def extract_and_show():
    if not image_path:
        messagebox.showerror("Error", "Please select an image first.")
        return
    try:
        if meta_path:
            output = extract_from_image_and_text(image_path, meta_path)
        else:
            output = extract_from_image(image_path)
        output_box.delete(1.0, tk.END)
        output_box.insert(tk.END, json.dumps(output, indent=2))
    except Exception as e:
        messagebox.showerror("Error", f"Failed to extract metadata: {e}")

def clear_all():
    """Reset everything for a new extraction."""
    global image_path, meta_path
    image_path = ""
    meta_path = ""
    entry_image.config(state="normal")
    entry_image.delete(0, tk.END)
    entry_image.config(state="readonly")
    entry_meta.config(state="normal")
    entry_meta.delete(0, tk.END)
    entry_meta.config(state="readonly")
    output_box.delete(1.0, tk.END)

# ------------------ UI Layout ------------------

root = tk.Tk()
root.title("SEM Image Metadata Extractor (Enhanced)")
root.geometry("1050x780")
root.configure(bg="#EAF0FB")

# Initialize global paths
image_path = ""
meta_path = ""

style = ttk.Style()
style.theme_use("clam")

# Header
header = tk.Frame(root, bg="#4A90E2", height=70)
header.pack(fill="x")
tk.Label(header, text="SEM Image Metadata Extractor",
         font=("Helvetica", 22, "bold"), fg="white", bg="#4A90E2").pack(pady=15)

frame = tk.Frame(root, bg="#EAF0FB")
frame.pack(pady=20)

# Image Input
ttk.Label(frame, text="Select SEM Image:", font=("Helvetica", 12, "bold"), background="#EAF0FB").grid(row=0, column=0, padx=10, sticky="e")
entry_image = tk.Entry(frame, width=70, font=("Arial", 11), bg="#FFF8DC", fg="#000000", relief="solid", bd=1)
entry_image.grid(row=0, column=1, padx=10)
entry_image.configure(state="readonly")
tk.Button(frame, text="📂 Browse", command=select_image, bg="#AED6F1", fg="black", font=("Helvetica", 10, "bold")).grid(row=0, column=2, padx=5)

# Metadata Input
ttk.Label(frame, text="Select Metadata File:", font=("Helvetica", 12, "bold"), background="#EAF0FB").grid(row=1, column=0, padx=10, sticky="e")
entry_meta = tk.Entry(frame, width=70, font=("Arial", 11), bg="#FDEBD0", fg="#000000", relief="solid", bd=1)
entry_meta.grid(row=1, column=1, padx=10)
entry_meta.configure(state="readonly")
tk.Button(frame, text="📁 Browse", command=select_metadata, bg="#F5B7B1", fg="black", font=("Helvetica", 10, "bold")).grid(row=1, column=2, padx=5)

# Buttons Frame
btn_frame = tk.Frame(root, bg="#EAF0FB")
btn_frame.pack(pady=15)

extract_btn = tk.Button(btn_frame, text="Extract & Show JSON", command=extract_and_show,
                        bg="#90EE90", fg="black", font=("Helvetica", 13, "bold"),
                        relief="raised", width=22, height=2, cursor="hand2", activebackground="#7CFC00")

clear_btn = tk.Button(btn_frame, text="Clear All", command=clear_all,
                      bg="#FFA07A", fg="black", font=("Helvetica", 13, "bold"),
                      relief="raised", width=15, height=2, cursor="hand2", activebackground="#FA8072")

extract_btn.grid(row=0, column=0, padx=15)
clear_btn.grid(row=0, column=1, padx=15)

# Output Box
output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=120, height=25,
                                       bg="#1E1E1E", fg="#00FF7F",
                                       insertbackground="white", relief="solid", bd=2,
                                       font=("Consolas", 11))
output_box.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

root.mainloop()
