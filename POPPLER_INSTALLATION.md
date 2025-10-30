# Poppler Installation Guide for DeltaCFOAgent

## What is Poppler?

Poppler is a PDF rendering library required for converting PDF files to images. DeltaCFOAgent uses it for:
- Transaction PDF uploads (Claude Vision processing)
- Invoice PDF processing (Invoice system)

## Why is it needed?

Both systems use the `pdf2image` Python library, which depends on Poppler binaries to:
1. Convert PDF pages to images
2. Allow Claude Vision AI to analyze PDF content
3. Extract transaction and invoice data from PDF documents

## Installation Instructions for Windows

### Option 1: Download Pre-built Binaries (Recommended)

1. **Download Poppler for Windows:**
   - Go to: https://github.com/oschwartz10612/poppler-windows/releases/
   - Download the latest release ZIP file (e.g., `Release-24.08.0-0.zip`)

2. **Extract to a permanent location:**
   ```
   Extract to: C:\Program Files\poppler
   ```

   After extraction, you should have:
   ```
   C:\Program Files\poppler\
   └── Library\
       └── bin\
           ├── pdfinfo.exe
           ├── pdftoppm.exe
           └── ... (other PDF tools)
   ```

3. **Add to Windows PATH:**

   a. Open Windows Search and type "Environment Variables"

   b. Click "Edit the system environment variables"

   c. Click "Environment Variables" button

   d. Under "System variables" (or "User variables"), find "Path"

   e. Click "Edit"

   f. Click "New" and add:
   ```
   C:\Program Files\poppler\Library\bin
   ```

   g. Click "OK" on all dialogs

   h. **IMPORTANT:** Restart your terminal/IDE/VSCode for changes to take effect

### Option 2: Using Chocolatey

If you have Chocolatey package manager installed:

```powershell
choco install poppler
```

### Option 3: Using Conda

If you use Anaconda/Miniconda:

```bash
conda install -c conda-forge poppler
```

## Verify Installation

After installation and restarting your terminal, verify poppler is working:

```bash
pdfinfo --version
```

You should see output like:
```
pdfinfo version 24.08.0
```

Or:
```bash
pdftoppm -h
```

Should show help text without errors.

## Troubleshooting

### Error: "Unable to get page count. Is poppler installed and in PATH?"

**Cause:** Poppler is not installed or not in PATH

**Solution:**
1. Verify installation folder exists
2. Verify PATH was added correctly
3. **Restart your terminal/IDE** (very important!)
4. Run verification command: `pdfinfo --version`

### Error: "PDF processing libraries not available"

**Cause:** Python packages not installed

**Solution:**
```bash
pip install pdf2image Pillow
```

### Still not working after installation?

1. **Verify PATH:**
   ```powershell
   $env:Path -split ';' | Select-String poppler
   ```
   Should show the poppler path.

2. **Verify binaries exist:**
   ```powershell
   Get-Command pdfinfo
   ```
   Should show the full path to pdfinfo.exe

3. **Restart everything:**
   - Close all terminals
   - Close VSCode/IDE
   - Reopen and try again

## What Features Require Poppler?

### With Poppler Installed:
- PDF transaction uploads
- PDF invoice processing
- Bank statement PDF imports
- Receipt PDF processing

### Works Without Poppler:
- CSV file uploads
- Image uploads (PNG, JPG)
- Manual transaction entry
- All other dashboard features

## Production Deployment

For Google Cloud Run or Docker deployments, poppler is installed via Dockerfile:

```dockerfile
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
```

No additional configuration needed in production.

## Additional Resources

- Poppler GitHub: https://github.com/oschwartz10612/poppler-windows
- pdf2image documentation: https://pypi.org/project/pdf2image/
- Troubleshooting: https://github.com/Belval/pdf2image#windows

## Need Help?

If you continue having issues:
1. Check the error message in the upload response
2. Verify poppler binaries are in PATH
3. Restart terminal/IDE after PATH changes
4. Try uploading a CSV file to verify system is working
