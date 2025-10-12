import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image
from pathlib import Path
import xml.etree.ElementTree as ET
import json, re, os, datetime
from sem_meta import SEMMeta
import fitz  # PyMuPDF
import pandas as pd

# ------------------ Helper Functions ------------------

image_path = ""
image_path2 = ""
meta_path2 = ""
pdf_path = ""
output_folder = ""

def strip_ns_key(key): return key.split('}')[-1] if '}' in key else key

def xml_to_dict(elem):
    children = list(elem)
    if not children:
        t = elem.text.strip() if elem.text and elem.text.strip() else None
        return t
    r = {}
    for c in children:
        d = xml_to_dict(c)
        t = strip_ns_key(c.tag)
        if t in r:
            if not isinstance(r[t], list): r[t] = [r[t]]
            r[t].append(d)
        else:
            r[t] = d
    return r

def strip_ns(d):
    if isinstance(d, dict):  return {strip_ns_key(k): strip_ns(v) for k,v in d.items()}
    if isinstance(d, list):  return [strip_ns(i) for i in d]
    return d

def parse_value(v):
    if v is None: return None
    if isinstance(v,(tuple,list)): return [parse_value(i) for i in v]
    if isinstance(v,bytes):
        try: v=v.decode("utf-8",errors="ignore")
        except: return None
    if isinstance(v,str):
        try:
            r=ET.fromstring(v)
            return {strip_ns_key(r.tag):xml_to_dict(r)}
        except ET.ParseError: pass
        if "=" in v:
            kv={}
            for line in v.splitlines():
                if "=" in line:
                    k,val=line.split("=",1)
                    kv[k.strip()]=val.strip()
            if kv: return {"plain":kv}
    try: json.dumps(v); return v
    except: return None

def convert_meta_to_json(meta):
    c={}
    for k,v in meta.items():
        try: c[str(k)]=strip_ns(parse_value(v))
        except: c[str(k)]=None
    return c

def parse_jeol_metadata(meta_path):
    d={}
    try:
        with open(meta_path,"r",encoding="utf-8",errors="ignore") as f:
            for line in f:
                line=line.strip()
                if line.startswith("$"):
                    m=re.match(r"^\$+([A-Z0-9_%]+)\s*(.*)$",line)
                    if m: k,v=m.groups(); d[k.strip()]=v.strip()
    except Exception as e:
        d={"Error":f"Failed to parse metadata: {e}"}
    return d

# ------------------ SEM Extraction ------------------

def extract_from_image(image_path):
    with Image.open(image_path) as im:
        meta,_=SEMMeta.ImageMetadata(im)
        return {"image":Path(image_path).name,"metadata":convert_meta_to_json(meta)}

def extract_from_image_and_text(image_path,meta_path):
    m=parse_jeol_metadata(meta_path)
    b=Path(image_path).stem
    mach=m.get("CM_INSTRUMENT","Unknown").strip()
    date=m.get("CM_DATE","Unknown").replace("/","-")
    u=f"{b}_{mach}_{date}"
    return {"id":b,"image_file":f"{u}.tif","metadata_file":f"{u}.txt",
            "machine":mach,"date_taken":date,"metadata":m}

def save_json(output_box, image_path):
    text=output_box.get(1.0,tk.END).strip()
    if not text: return messagebox.showwarning("No Data","Nothing to save.")
    try: data=json.loads(text)
    except: return messagebox.showerror("Error","Invalid JSON.")
    base=Path(image_path).stem+"_metadata.json" if image_path else "metadata.json"
    init_dir=str(Path(image_path).parent) if image_path else os.getcwd()
    path=filedialog.asksaveasfilename(defaultextension=".json",
        filetypes=[("JSON","*.json")],initialfile=base,initialdir=init_dir)
    if not path: return
    try:
        with open(path,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
        messagebox.showinfo("Saved",f"Saved → {path}")
    except Exception as e:
        messagebox.showerror("Error",f"Failed to save:\n{e}")

def clear_all(entries,box):
    for e in entries:
        e.config(state="normal"); e.delete(0,tk.END); e.config(state="readonly")
    box.delete(1.0,tk.END)

# ------------------ PDF Extraction ------------------

def extract_images_from_pdf(pdf_path, output_folder, output_box):
    """Extract all images and metadata from PDF into auto-created subfolder."""
    if not pdf_path:
        return messagebox.showerror("Error", "Please select a PDF file first.")
    if not output_folder:
        return messagebox.showerror("Error", "Please select a base output folder.")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    full_output_path = os.path.join(output_folder, f"Extracted_Images_{timestamp}")
    os.makedirs(full_output_path, exist_ok=True)

    try:
        doc = fitz.open(pdf_path)
        metadata_list = []

        for page_index in range(len(doc)):
            page = doc[page_index]
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                width = base_image["width"]
                height = base_image["height"]
                colorspace = base_image["colorspace"]
                bpc = base_image["bpc"]

                image_filename = f"page{page_index+1}_img{img_index+1}.{image_ext}"
                image_path = os.path.join(full_output_path, image_filename)

                with open(image_path, "wb") as f:
                    f.write(image_bytes)

                metadata_list.append({
                    "Page": page_index + 1,
                    "Image Number": img_index + 1,
                    "Filename": image_filename,
                    "Width (px)": width,
                    "Height (px)": height,
                    "Extension": image_ext,
                    "Color Space": colorspace,
                    "Bits per Component": bpc,
                    "File Path": image_path
                })

        df = pd.DataFrame(metadata_list)
        excel_path = os.path.join(full_output_path, "image_metadata.xlsx")
        df.to_excel(excel_path, index=False)

        output_box.delete(1.0, tk.END)
        output_box.insert(tk.END, f"✅ Extracted {len(metadata_list)} images\n")
        output_box.insert(tk.END, f"📁 Saved in: {full_output_path}\n")
        output_box.insert(tk.END, f"🧾 Metadata Excel: {excel_path}\n")

        messagebox.showinfo("Success", f"Extracted {len(metadata_list)} images.\nSaved to:\n{full_output_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to extract images:\n{e}")

# ------------------ GUI Layout ------------------

root = tk.Tk()
root.title("SEM + PDF Metadata Extractor")
root.geometry("1080x820")
root.configure(bg="#EAF0FB")
style = ttk.Style(); style.theme_use("clam")

header = tk.Frame(root, bg="#4A90E2", height=70)
header.pack(fill="x")
tk.Label(header, text="SEM & PDF Image Metadata Extractor",
         font=("Helvetica", 22, "bold"), fg="white", bg="#4A90E2").pack(pady=15)

# Notebook (Tabs)
notebook = ttk.Notebook(root)
notebook.pack(padx=10, pady=10, fill="x")

# --- Tabs ---
tab1 = tk.Frame(notebook, bg="#EAF0FB")
tab2 = tk.Frame(notebook, bg="#EAF0FB")
tab3 = tk.Frame(notebook, bg="#EAF0FB")
notebook.add(tab1, text="🖼 Image Only")
notebook.add(tab2, text="🧾 Image + Metadata File")
notebook.add(tab3, text="📘 PDF Image Extractor")

# Shared Output
output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=120, height=25,
    bg="#1E1E1E", fg="#00FF7F", insertbackground="white", relief="solid", bd=2,
    font=("Consolas", 11))
output_box.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

# Clear output when tab changes
def on_tab_change(event):
    output_box.delete(1.0, tk.END)
notebook.bind("<<NotebookTabChanged>>", on_tab_change)

# ------------------ Tab 1: Image Only ------------------

tk.Label(tab1, text="Select SEM Image:", bg="#EAF0FB", font=("Helvetica", 12, "bold")).grid(row=0, column=0, padx=10, sticky="e")
entry_img1 = tk.Entry(tab1, width=70, font=("Arial", 11), bg="#FFF8DC", relief="solid", bd=1, state="readonly")
entry_img1.grid(row=0, column=1, padx=10)

def browse_img1():
    global image_path
    image_path = filedialog.askopenfilename(title="Select SEM Image",
        filetypes=[("SEM Images", "*.tif *.tiff *.bmp *.jpg *.jpeg *.png")])
    if image_path:
        entry_img1.config(state="normal"); entry_img1.delete(0, tk.END)
        entry_img1.insert(0, image_path); entry_img1.config(state="readonly")

tk.Button(tab1, text="📂 Browse", command=browse_img1, bg="#AED6F1", font=("Helvetica", 10, "bold")).grid(row=0, column=2, padx=5)

ttk.Button(tab1, text="Extract & Show", command=lambda: (
    output_box.delete(1.0, tk.END),
    output_box.insert(tk.END, json.dumps(extract_from_image(image_path), indent=2)) if image_path else messagebox.showerror("Error","Select an image first.")
)).grid(row=1, column=0, padx=10, pady=10)
ttk.Button(tab1, text="Save JSON", command=lambda: save_json(output_box, image_path)).grid(row=1, column=1, padx=10)
ttk.Button(tab1, text="Clear", command=lambda: clear_all([entry_img1], output_box)).grid(row=1, column=2, padx=10)

# ------------------ Tab 2: Image + Metadata ------------------

tk.Label(tab2, text="Select SEM Image:", bg="#EAF0FB", font=("Helvetica", 12, "bold")).grid(row=0, column=0, padx=10, sticky="e")
entry_img2 = tk.Entry(tab2, width=70, font=("Arial", 11), bg="#FFF8DC", relief="solid", bd=1, state="readonly")
entry_img2.grid(row=0, column=1, padx=10)

tk.Label(tab2, text="Select Metadata File:", bg="#EAF0FB", font=("Helvetica", 12, "bold")).grid(row=1, column=0, padx=10, sticky="e")
entry_meta2 = tk.Entry(tab2, width=70, font=("Arial", 11), bg="#FDEBD0", relief="solid", bd=1, state="readonly")
entry_meta2.grid(row=1, column=1, padx=10)

def browse_img2():
    global image_path2
    image_path2 = filedialog.askopenfilename(title="Select SEM Image", filetypes=[("SEM Images", "*.tif *.tiff *.bmp *.jpg *.jpeg *.png")])
    if image_path2:
        entry_img2.config(state="normal"); entry_img2.delete(0, tk.END)
        entry_img2.insert(0, image_path2); entry_img2.config(state="readonly")

def browse_meta2():
    global meta_path2
    meta_path2 = filedialog.askopenfilename(title="Select Metadata File", filetypes=[("Text files", "*.txt")])
    if meta_path2:
        entry_meta2.config(state="normal"); entry_meta2.delete(0, tk.END)
        entry_meta2.insert(0, meta_path2); entry_meta2.config(state="readonly")

tk.Button(tab2, text="📂 Browse", command=browse_img2, bg="#AED6F1", font=("Helvetica", 10, "bold")).grid(row=0, column=2, padx=5)
tk.Button(tab2, text="📁 Browse", command=browse_meta2, bg="#F5B7B1", font=("Helvetica", 10, "bold")).grid(row=1, column=2, padx=5)

ttk.Button(tab2, text="Extract & Show", command=lambda: (
    output_box.delete(1.0, tk.END),
    output_box.insert(tk.END, json.dumps(extract_from_image_and_text(image_path2, meta_path2), indent=2)) if (image_path2 and meta_path2) else messagebox.showerror("Error","Select both image and metadata file.")
)).grid(row=2, column=0, padx=10, pady=10)
ttk.Button(tab2, text="Save JSON", command=lambda: save_json(output_box, globals().get("image_path2",""))).grid(row=2, column=1, padx=10)
ttk.Button(tab2, text="Clear", command=lambda: clear_all([entry_img2, entry_meta2], output_box)).grid(row=2, column=2, padx=10)

# ------------------ Tab 3: PDF Extractor ------------------

tk.Label(tab3, text="Select PDF File:", bg="#EAF0FB", font=("Helvetica", 12, "bold")).grid(row=0, column=0, padx=10, sticky="e")
entry_pdf = tk.Entry(tab3, width=70, font=("Arial", 11), bg="#E8F8F5", relief="solid", bd=1, state="readonly")
entry_pdf.grid(row=0, column=1, padx=10)

tk.Label(tab3, text="Select Base Output Folder:", bg="#EAF0FB", font=("Helvetica", 12, "bold")).grid(row=1, column=0, padx=10, sticky="e")
entry_output = tk.Entry(tab3, width=70, font=("Arial", 11), bg="#FDEBD0", relief="solid", bd=1, state="readonly")
entry_output.grid(row=1, column=1, padx=10)

def browse_pdf():
    global pdf_path
    pdf_path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF files", "*.pdf")])
    if pdf_path:
        entry_pdf.config(state="normal"); entry_pdf.delete(0, tk.END)
        entry_pdf.insert(0, pdf_path); entry_pdf.config(state="readonly")

def browse_output_folder():
    global output_folder
    output_folder = filedialog.askdirectory(title="Select Output Folder")
    if output_folder:
        entry_output.config(state="normal"); entry_output.delete(0, tk.END)
        entry_output.insert(0, output_folder); entry_output.config(state="readonly")

tk.Button(tab3, text="📘 Browse PDF", command=browse_pdf, bg="#AED6F1", font=("Helvetica", 10, "bold")).grid(row=0, column=2, padx=5)
tk.Button(tab3, text="📂 Choose Folder", command=browse_output_folder, bg="#F5B7B1", font=("Helvetica", 10, "bold")).grid(row=1, column=2, padx=5)
ttk.Button(tab3, text="Extract Images + Metadata", command=lambda: extract_images_from_pdf(pdf_path, output_folder, output_box)).grid(row=2, column=1, pady=15)
ttk.Button(tab3, text="Clear", command=lambda: clear_all([entry_pdf, entry_output], output_box)).grid(row=2, column=2, padx=10)

root.mainloop()
