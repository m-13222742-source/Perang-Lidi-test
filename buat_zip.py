import os
import zipfile

# Laluan lokasi simpanan fail ZIP
LOKASI_OUTPUT_ZIP = r'C:\Users\zarif\Perang_Lidi_:_The Stickman War.zip'

def buat_fail_zip():
    # Memastikan folder sasaran wujud
    folder_sasaran = os.path.dirname(LOKASI_OUTPUT_ZIP)
    if folder_sasaran and not os.path.exists(folder_sasaran):
        os.makedirs(folder_sasaran)

    print("⚡ Sedang memampatkan fail projek...")

    with zipfile.ZipFile(LOKASI_OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            for file in files:
                # HANYA ABAIKAN FAIL INI SAHAJA
                if file == 'buat_zip.py':
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, '.')
                zipf.write(file_path, arcname)
                
    print(f"✅ Berjaya! Fail ZIP telah dicipta di: {LOKASI_OUTPUT_ZIP}")

if __name__ == '__main__':
    buat_fail_zip()