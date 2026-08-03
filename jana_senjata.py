# jana_senjata.py
from ursina import Entity, color, destroy

def bina_model_senjata(nama_senjata, entiti_pemegang):
    """
    Fungsi ini akan membuang senjata lama dan membina 
    model 3D senjata baharu menggunakan bentuk primitif Ursina.
    """
    # 1. Buang model senjata lama setiap kali tukar senjata
    for anak in entiti_pemegang.children:
        destroy(anak)
        
    # 2. Jana bentuk senjata baharu berdasarkan nama
    if nama_senjata == "Tangan Kosong":
        pass # Tiada visual

    elif nama_senjata == "Pedang Buluh":
        # Bilah hijau/coklat
        Entity(parent=entiti_pemegang, model='cube', color=color.rgb(100, 200, 100), scale=(0.1, 1.5, 0.2), position=(0, 0.5, 0))
        # Pemegang
        Entity(parent=entiti_pemegang, model='cube', color=color.brown, scale=(0.15, 0.3, 0.25), position=(0, -0.4, 0)) 

    elif nama_senjata == "Busur Panah":
        # Badan Busur (Melengkung)
        Entity(parent=entiti_pemegang, model='cube', color=color.brown, scale=(0.1, 1.2, 0.1), position=(0, 0.5, 0.2), rotation_x=15)
        Entity(parent=entiti_pemegang, model='cube', color=color.brown, scale=(0.1, 1.2, 0.1), position=(0, -0.5, 0.2), rotation_x=-15)
        # Tali Panah
        Entity(parent=entiti_pemegang, model='cube', color=color.white, scale=(0.02, 2.2, 0.02), position=(0, 0, -0.1))

    elif nama_senjata == "Lembing":
        # Batang Panjang
        Entity(parent=entiti_pemegang, model='cylinder', color=color.brown, scale=(0.1, 2.5, 0.1), position=(0, 0.8, 0))
        # Mata Lembing (Tajam)
        Entity(parent=entiti_pemegang, model='cone', color=color.light_gray, scale=(0.15, 0.6, 0.15), position=(0, 2.3, 0))

    elif nama_senjata == "Scythe":
        # Batang Sabit
        Entity(parent=entiti_pemegang, model='cylinder', color=color.dark_gray, scale=(0.1, 2.5, 0.1), position=(0, 0.8, 0))
        # Bilah Melintang
        Entity(parent=entiti_pemegang, model='cube', color=color.light_gray, scale=(0.1, 0.2, 1.2), position=(0, 2.0, 0.5), rotation_x=20)
        Entity(parent=entiti_pemegang, model='cone', color=color.light_gray, scale=(0.1, 0.8, 0.2), position=(0, 1.8, 1.0), rotation_x=110)

    elif nama_senjata == "Lembing Beracun":
        # Batang
        Entity(parent=entiti_pemegang, model='cylinder', color=color.brown, scale=(0.1, 2.5, 0.1), position=(0, 0.8, 0))
        # Mata Lembing Berwarna Hijau Menyala (Racun)
        Entity(parent=entiti_pemegang, model='cone', color=color.lime, scale=(0.18, 0.6, 0.18), position=(0, 2.3, 0))