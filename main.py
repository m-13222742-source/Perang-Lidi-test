from ursina import *
from ursina.models.procedural.cylinder import Cylinder 
import random
import math
import socket
import threading
import binascii
import base64
import sys
import time

# --- PENGENDALIAN IMPORT ASET EXTERNAL SAFELY ---
try:
    from jana_senjata import bina_model_senjata
except ImportError:
    # Fallback sederhana jika modul jana_senjata tiada
    def bina_model_senjata(nama_senjata, parent_entity):
        parent_entity.model = 'cube'
        parent_entity.color = color.gray

# --- DEFINISI TEXT3D UNTUK PAPARAN TEKS DALAM DUNIA 3D ---
class Text3D(Text):
    def __init__(self, **kwargs):
        if 'billboard' not in kwargs:
            kwargs['billboard'] = True
        super().__init__(**kwargs)

# --- FUNGSI PEMBANTU HALA SUDUT ---
def lerp_angle(a, b, t):
    diff = (b - a + 180) % 360 - 180
    return a + diff * t

# --- 1. SET UNTUK SKOP GLOBAL & RANGKAIAN ---
game_berjalan = False  
pemain_hidup = True
pemain_diburu_pulau = False 

KELAJUAN_JALAN = 12    
KELAJUAN_SPRINT = 22   
KELAJUAN_DASH = 55     
kecepatan_jalan = KELAJUAN_JALAN  

kelajuan_askar = 8
kelajuan_musuh = 5
global_penceroboh = None  

HOST_IP = '127.0.0.1'  
PORT = 7777
soket_client = None
soket_server = None
senarai_client = []
status_rangkaian = None  

MAX_PEMAIN = 10
MIN_PEMAIN = 2

skrin_bsod_palsu = None

senjata_stats = {
    "Tangan Kosong": {"damage": 5, "range": 3.0, "type": "melee", "poison": False},
    "Pedang Buluh": {"damage": 20, "range": 4.0, "type": "melee", "poison": False},
    "Busur Panah": {"damage": 25, "range": 50.0, "type": "ranged", "poison": False},
    "Lembing": {"damage": 35, "range": 6.5, "type": "melee", "poison": False},
    "Scythe": {"damage": 50, "range": 5.0, "type": "melee", "poison": False},
    "Lembing Beracun": {"damage": 25, "range": 6.5, "type": "melee", "poison": True}
}

try:
    from ursina.prefabs.health_bar import HealthBar 
except ImportError:
    class HealthBar(Button):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.max_value = kwargs.get('max_value', 100)
            self.value = kwargs.get('value', 100)
            self.bar = Entity(parent=self, model='quad', color=kwargs.get('bar_color', color.red), origin=(-0.5,0), scale=(1,1))
        @property
        def value(self): return self._value
        @value.setter
        def value(self, v):
            self._value = v
            if hasattr(self, 'bar') and hasattr(self, 'max_value'):
                self.bar.scale_x = max(0.0, min(1.0, v / self.max_value))

app = Ursina(title="Perang Lidi: Edisi Raksasa Laut & Glitch Terapung")
window.exit_button.visible = False 
application.development_mode = False 
window.color = color.cyan 

# --- AUDIO MAIN MENU ---
senarai_lagu = ['Perang_Lidi_Main_Menu_OST.wav']
musik_menu = None

def mainkan_lagu_menu():
    global musik_menu
    hentikan_lagu_menu() 
    try:
        lagu_terpilih = random.choice(senarai_lagu)
        musik_menu = Audio(lagu_terpilih, loop=True, autoplay=True, volume=0.5)
    except Exception:
        musik_menu = None

def hentikan_lagu_menu():
    global musik_menu
    if musik_menu and musik_menu.playing:
        musik_menu.stop()
        destroy(musik_menu)
        musik_menu = None

lampu_sekeliling = AmbientLight(color=color.rgba(120, 120, 120, 255))
lampu_utama = DirectionalLight()
lampu_utama.look_at(Vec3(1, -2, 1))

# --- 2. BINA DUNIA / LANTAI & GEOGRAFI ---
laut = Entity(model='plane', color=color.rgb(10, 80, 150), scale=(25000, 1, 25000), position=(0, -2, 0))
benua_tanah = Entity(model='cube', color=color.rgb(101, 67, 33), scale=(3000, 3, 3000), position=(0, -1.5, 0), collider='box')
benua_rumput = Entity(model='plane', color=color.rgb(34, 139, 34), scale=(3000, 1, 3000), position=(0, 0.01, 0))
pulau_tanah = Entity(model='cube', color=color.rgb(101, 67, 33), scale=(800, 3, 800), position=(1800, -1.5, 1800), collider='box')
pulau_rumput = Entity(model='plane', color=color.rgb(34, 139, 34), scale=(800, 1, 800), position=(1800, 0.01, 1800))
sungai = Entity(model='plane', color=color.rgb(30, 144, 255), scale=(80, 1, 3000), position=(400, 0.02, 0))

# --- 2.5 SISTEM HUJAN ---
titisan_hujan = []
hujan_aktif = False 
pemasa_cuaca = random.uniform(20.0, 60.0) 

def jana_sistem_hujan():
    for _ in range(150): 
        titis = Entity(model='cube', color=color.rgba(100, 150, 255, 150), scale=(0.03, 1.2, 0.03), enabled=False)
        titis.x = random.uniform(-50, 50)
        titis.y = random.uniform(10, 50)
        titis.z = random.uniform(-50, 50)
        titisan_hujan.append(titis)

invoke(jana_sistem_hujan, delay=0.5)

def kemas_kini_hujan():
    global hujan_aktif, pemasa_cuaca
    pemasa_cuaca -= time.dt
    
    if pemasa_cuaca <= 0:
        hujan_aktif = not hujan_aktif 
        if hujan_aktif:
            pemasa_cuaca = random.uniform(30.0, 120.0)
            if 'butang_bahasa' in globals():
                teks_dialog.text = "Sistem: Cuaca berubah... Hujan mula turun." if "Language: Malay" in butang_bahasa.text else "System: Weather changing... It started to rain."
        else:
            pemasa_cuaca = random.uniform(60.0, 180.0)
            if 'butang_bahasa' in globals():
                teks_dialog.text = "Sistem: Hujan telah reda. Cuaca kembali cerah." if "Language: Malay" in butang_bahasa.text else "System: The rain has stopped. Weather is clear."

    if not hujan_aktif:
        for titis in titisan_hujan: 
            if titis.enabled: titis.enabled = False
        return
        
    for titis in titisan_hujan:
        if not titis.enabled:
            titis.enabled = True
            titis.x = pemain.x + random.uniform(-45, 45)
            titis.y = pemain.y + random.uniform(20, 50)
            titis.z = pemain.z + random.uniform(-45, 45)

        titis.y -= 40 * time.dt 
        if titis.y < 0:
            titis.x = pemain.x + random.uniform(-45, 45)
            titis.y = pemain.y + random.uniform(20, 40)
            titis.z = pemain.z + random.uniform(-45, 45)

def muat_mesh_obj_selamat(nama_fail):
    try:
        from ursina import load_model
        mesh_load = load_model(nama_fail)
        if mesh_load:
            return mesh_load
    except Exception:
        pass
    return 'cube'

# --- 4. PEMAIN UTAMA & DATA INVENTORI ---
pemain = Entity(
    position=(0, 0, -20), 
    model=muat_mesh_obj_selamat('Pemain_Smooth.glb'), 
    color=color.black, 
    scale=(1, 1, 1),           
    collider='box'
)
pemain.pemasa_animasi = 0
pemain.y_velocity = 0 
pemain.darah_maksimum = 150
pemain.darah = 150
pemain.sanity_maksimum = 100
pemain.sanity = 100
pemain.oksigen_maksimum = 100
pemain.oksigen = 100
pemain.xp_maksimum = 30
pemain.xp = 0  
pemain.tahap = 1
pemain.sedang_diserang_oleh = None 
pemain.dalam_penjara = False
pemain.masa_penjara = 0

pemain.cooldown_dash = 0.0
pemain.pemasa_dash = 0.0

pemain.slot_senjata = "Pedang Buluh"  
pemain.slot_syiling = "Syiling Upgrade" 
pemain.inventori = ["Pedang Buluh", "Busur Panah", "Lembing", "Scythe", "Lembing Beracun", "Alatan Ubatan", "Roti", "Air Minuman"]
pemain.cooldown_diserang = 0.0

pemain.model_senjata = Entity(
    parent=pemain, 
    model=None, 
    scale=(0.8, 0.8, 0.8), 
    position=(0.6, 1, 0.5), 
    rotation_x=90
)

bina_model_senjata(pemain.slot_senjata, pemain.model_senjata)

pemain.kunci_bsod = False
pemain.kunci_gerak_bsod = {'w': False, 'a': False, 's': False, 'd': False}

# --- KAMERA ORBIT ---
kamera_pivot = Entity()
camera.parent = kamera_pivot
camera.position = (0, 3.5, -11)  
camera.rotation_x = 18           
sensitiviti_tetikus = 150
mouse.locked = False             

# --- 5. BINA LOKASI PENJARA AWAN ---
penjara_pusat = (1000, 150, 1000) 
Entity(model='plane', color=color.rgb(30, 30, 30), scale=(40, 1, 40), position=penjara_pusat, collider='box')
Entity(model='cube', color=color.gray, scale=(40, 15, 1), position=(1000, 157.5, 1020), collider='box')
Entity(model='cube', color=color.gray, scale=(40, 15, 1), position=(1000, 157.5, 980), collider='box')
Entity(model='cube', color=color.gray, scale=(1, 15, 40), position=(1020, 157.5, 1000), collider='box')
for i in range(20): 
    Entity(model='cube', color=color.dark_gray, scale=(0.5, 15, 1), position=(980.5, 157.5, 981 + (i*2)), collider='box')

# --- 6. ENTITI PERMAINAN & KELAS KHAS ---
senarai_npc = []
senarai_musuh = []
senarai_musuh_pulau = [] 
senarai_askar = []
senarai_objek_pejal = [] 
senarai_pintu = []  
senarai_pemanah = []
senarai_pemain_multiplayer = []

def daftar_objek_pejal(entiti, saiz_pelanggaran=2.5):
    entiti.saiz_pelanggaran = saiz_pelanggaran
    senarai_objek_pejal.append(entiti)

def pembersihan_entiti_mati():
    """Membuang entiti yang dinyahaktifkan daripada senarai sistem bagi menjaga prestasi."""
    global senarai_musuh, senarai_npc, senarai_askar, senarai_pemanah, senarai_musuh_pulau
    senarai_musuh = [m for m in senarai_musuh if m and m.enabled]
    senarai_npc = [n for n in senarai_npc if n and n.enabled]
    senarai_askar = [a for a in senarai_askar if a and a.enabled]
    senarai_pemanah = [p for p in senarai_pemanah if p and p.enabled]
    senarai_musuh_pulau = [mp for mp in senarai_musuh_pulau if mp and mp.enabled]

class Pintu(Entity):
    def __init__(self, position=(0, 0, 0), scale=(6, 5, 0.2), rotation_y=0, **kwargs):
        warna = kwargs.pop('color', color.brown)
        super().__init__(model='cube', color=warna, position=position, scale=scale, rotation_y=rotation_y, **kwargs)
        self.is_closed = True
        self.original_rotation_y = rotation_y
        self.hitbox_asal = 2.0 
    def toggle(self):
        if self.is_closed:
            self.rotation_y = self.original_rotation_y + 90 
            self.is_closed = False; self.saiz_pelanggaran = 0.0 
        else:
            self.rotation_y = self.original_rotation_y 
            self.is_closed = True; self.saiz_pelanggaran = self.hitbox_asal

class AnakPanah(Entity):
    def __init__(self, posisi, sasaran, **kwargs):
        super().__init__(model='cube', color=color.black, scale=(0.1, 0.1, 1.5), position=posisi, **kwargs)
        self.sasaran = sasaran; self.kelajuan = 45
        self.look_at(self.sasaran.position + Vec3(0, 1, 0))
        self.nama = "Pemanah Lidi" 
    def update(self):
        if not self.sasaran or not self.sasaran.enabled or getattr(self.sasaran, 'darah', 1) <= 0 or getattr(self.sasaran, 'status', '') == "DIPENJARA":
            destroy(self); return
        self.position += self.forward * self.kelajuan * time.dt
        if distance(self.position, self.sasaran.position) < 2.5:
            if hasattr(self.sasaran, 'darah'): self.sasaran.darah -= 15 
            elif hasattr(self.sasaran, 'hp_semasa'):
                self.sasaran.hp_semasa -= 15
                self.sasaran.kemas_kini_hp(self.sasaran.hp_semasa)
            if self.sasaran == pemain: pemain.sedang_diserang_oleh = self
            destroy(self) 

class LembingTerbang(Entity):
    def __init__(self, posisi, sasaran, **kwargs):
        super().__init__(model='cylinder', color=color.rgb(139, 69, 19), scale=(0.08, 2.2, 0.08), position=posisi, **kwargs)
        self.sasaran = sasaran
        self.kelajuan = 40
        self.rotation_x = 90
        self.look_at(self.sasaran.position + Vec3(0, 1.2, 0))
    def update(self):
        if not self.sasaran or not self.sasaran.enabled or getattr(self.sasaran, 'darah', 1) <= 0:
            destroy(self); return
        self.position += self.forward * self.kelajuan * time.dt
        if distance(self.position, self.sasaran.position) < 2.5:
            if hasattr(self.sasaran, 'darah'): 
                self.sasaran.darah -= 35 
            destroy(self)
        elif self.y < 0 or distance(self.position, self.sasaran.position) > 150:
            destroy(self)

class AnakPanahPemain(Entity):
    def __init__(self, posisi, arah, damage_panah, beracun=False, **kwargs):
        super().__init__(model='cube', color=color.yellow if not beracun else color.lime, scale=(0.15, 0.15, 2.0), position=posisi, **kwargs)
        self.arah = arah; self.kelajuan = 55; self.damage = damage_panah; self.beracun = beracun
        self.look_at(self.position + self.arah); self.masa_hayat = 2.0 
    def update(self):
        self.position += self.forward * self.kelajuan * time.dt
        self.masa_hayat -= time.dt
        if self.masa_hayat <= 0: destroy(self); return
        
        for m in senarai_musuh + senarai_npc:
            if m and m.enabled and getattr(m, 'darah', 0) > 0 and getattr(m, 'status', '') != "DIPENJARA":
                if distance(self.position, m.position) < 2.5:
                    damage_akhir = self.damage
                    if getattr(m, 'perisai_aktif', False):
                        damage_akhir *= 0.3 if getattr(m, 'is_ketua_pulau', False) else 0.4
                    m.darah -= damage_akhir
                    if self.beracun: m.racun_timer = 5.0
                    if getattr(m, 'is_npc_campung', False) and not m.sudah_melapor:
                        m.status = "LARI_REPOT"; m.penyerang = pemain 
                        m.hp_text.text = "TOLONG! NAK REPOT ASKAR!"; m.hp_text.color = color.orange
                    destroy(self); return

class BatuCatapult(Entity):
    def __init__(self, posisi, sasaran, **kwargs):
        super().__init__(model='sphere', color=color.dark_gray, scale=(1.5, 1.5, 1.5), position=posisi, collider='sphere', **kwargs)
        self.sasaran = sasaran
        self.kelajuan = 25
        self.look_at(self.sasaran.position)
        
    def update(self):
        self.position += self.forward * self.kelajuan * time.dt
        self.y -= 5 * time.dt 
        
        if self.y < 0 or distance(self.position, self.sasaran.position) < 3.0:
            if distance(self.position, pemain.position) < 4.0:
                pemain.darah -= 45 
            destroy(self)

batang_kayu = Entity(model='cube', color=color.brown, scale=(0.4, 4, 0.4), position=(12, 1, -10), rotation_z=75)
daftar_objek_pejal(batang_kayu, 1.0)

class PemainMultiplayer(Entity):
    def __init__(self, posisi_awal, nama_pemain="Pemain Lain"):
        super().__init__(position=posisi_awal)
        self.nama = nama_pemain; self.hp_maks = 150; self.hp_semasa = 150
        self.model = muat_mesh_obj_selamat('Pemain_Smooth.obj')
        self.color = color.azure; self.scale = (1, 1, 1); self.collider = 'box'
        self.bar_bg = Entity(parent=self, model='quad', color=color.red, scale=(1.5, 0.15), position=(0, 2.5, 0), billboard=True)
        self.bar_hijau = Entity(parent=self.bar_bg, model='quad', color=color.green, scale=(1, 1), position=(0, 0, -0.01), origin=(-0.5, 0))
        self.teks_nama = Text3D(text=self.nama, parent=self, position=(0, 2.8, 0), scale=0.8, color=color.yellow, billboard=True, origin=(0, 0))

    def kemas_kini_hp(self, hp_baru):
        self.hp_semasa = max(0, min(hp_baru, self.hp_maks))
        self.bar_hijau.scale_x = self.hp_semasa / self.hp_maks
        if self.hp_semasa <= 0:
            self.bar_hijau.enabled = False
            self.teks_nama.text = f"{self.nama} (MATI)"; self.teks_nama.color = color.gray

# --- 7. SISTEM TAPISAN CHAT ---
KOD_CIPHER_BERLAPIS = "5a335270644730785a325a6e626a466d63323975633277786547356d63544631656e42754d577875635759785a325a7a62475a7a6244466e616e646d634446355a6d35774d58687561665a34616e7471637a463862575a354a58617461695672656d68774d5878745a6e6b61655731714a573171635845785a33646d626e4e3364486b785a33646d626e4e3364486b61654735394d6e68716532707a"

def nyahkod_senarai_rahsia(kod_sulit):
    try:
        dec_1 = binascii.unhexlify(kod_sulit)
        dec_2 = base64.b64decode(dec_1).decode('utf-8')
        dec_3 = "".join([chr(ord(c) - 5) for c in dec_2])
        return dec_3.split(',')
    except Exception: 
        return []

PERKATAAN_DILARANG = nyahkod_senarai_rahsia(KOD_CIPHER_BERLAPIS)
senarai_teks_chat = []; kotak_input_chat = None; kontena_chat = None  

def tapis_perkataan(teks):
    teks_rendah = teks.lower()
    for perkataan in PERKATAAN_DILARANG:
        if perkataan and perkataan in teks_rendah:
            teks = teks.replace(perkataan, "*" * len(perkataan))
    return teks

def hantar_mesej_chat():
    global kotak_input_chat
    if kotak_input_chat and kotak_input_chat.text.strip() != "":
        mesej_bersih = tapis_perkataan(kotak_input_chat.text)
        tambah_ke_log_chat(f"Pemain 1: {mesej_bersih}")
        kotak_input_chat.text = ""; kotak_input_chat.active = False 

def tambah_ke_log_chat(teks_baharu):
    global senarai_teks_chat, kontena_chat
    if not kontena_chat: return
    senarai_teks_chat.append(teks_baharu)
    if len(senarai_teks_chat) > 5: senarai_teks_chat.pop(0)
    kontena_chat.text = "\n".join(senarai_teks_chat)

def bina_ui_chat_multiplayer():
    global kotak_input_chat, kontena_chat
    kontena_chat = Text(text="", position=(-0.85, -0.1), scale=1.3, color=color.white, background=True)
    kotak_input_chat = InputField(position=(-0.65, -0.3), scale=(0.4, 0.04), placeholder='Tekan ENTER untuk menaip...', color=color.black66)
    kotak_input_chat.on_submit = hantar_mesej_chat

# --- 8. PEMBINA GLITCH VISUAL ---
def pasang_badan_lidi_glitch(entiti_induk, warna_lidi, tahap):
    faktor_herot = tahap * 0.35 
    def dapat_jarak_glitch():
        return (random.uniform(-faktor_herot, faktor_herot), random.uniform(-faktor_herot, faktor_herot), random.uniform(-faktor_herot, faktor_herot))

    hx, hy, hz = dapat_jarak_glitch()
    skala_kepala = 0.6 + random.uniform(-0.15, 0.2) * (tahap * 0.5)
    Entity(parent=entiti_induk, model='sphere', color=warna_lidi, scale=(skala_kepala, skala_kepala, skala_kepala), position=(hx, 1.8 + hy, hz))
    
    bx, by, bz = dapat_jarak_glitch()
    Entity(parent=entiti_induk, model=Cylinder(resolution=8), color=warna_lidi, scale=(0.15 + random.uniform(-0.05, 0.1)*tahap, 1.2, 0.15), position=(bx, 0.9 + by, bz), rotation=(random.uniform(-25, 25)*tahap, 0, random.uniform(-25, 25)*tahap))
    
    tx1, ty1, tz1 = dapat_jarak_glitch()
    Entity(parent=entiti_induk, model=Cylinder(resolution=6), color=warna_lidi, scale=(0.08, 0.8, 0.08), position=(-0.3 + tx1, 1.1 + ty1, tz1), rotation_z=15 + random.uniform(-50, 50)*tahap)
    tx2, ty2, tz2 = dapat_jarak_glitch()
    Entity(parent=entiti_induk, model=Cylinder(resolution=6), color=warna_lidi, scale=(0.08, 0.8, 0.08), position=(0.3 + tx2, 1.1 + ty2, tz2), rotation_z=-15 + random.uniform(-50, 50)*tahap)
    
    kx1, ky1, kz1 = dapat_jarak_glitch()
    Entity(parent=entiti_induk, model=Cylinder(resolution=6), color=warna_lidi, scale=(0.1, 0.9 + random.uniform(-0.2, 0.3)*tahap, 0.1), position=(-0.2 + kx1, 0.45 + ky1, kz1), rotation_x=random.uniform(-30, 30)*tahap)
    kx2, ky2, kz2 = dapat_jarak_glitch()
    Entity(parent=entiti_induk, model=Cylinder(resolution=6), color=warna_lidi, scale=(0.1, 0.9 + random.uniform(-0.2, 0.3)*tahap, 0.1), position=(0.2 + kx2, 0.45 + ky2, kz2), rotation_x=random.uniform(-30, 30)*tahap)

def hilangkan_bsod():
    global skrin_bsod_palsu
    if skrin_bsod_palsu:
        skrin_bsod_palsu.enabled = False
        pemain.kunci_bsod = False

def pasang_tangan_kaki_normal(entiti_induk, warna_lidi):
    Entity(parent=entiti_induk, model=Cylinder(resolution=6), color=warna_lidi, scale=(0.08, 0.8, 0.08), position=(-0.3, 1.1, 0), rotation_z=15)
    Entity(parent=entiti_induk, model=Cylinder(resolution=6), color=warna_lidi, scale=(0.08, 0.8, 0.08), position=(0.3, 1.1, 0), rotation_z=-15)
    Entity(parent=entiti_induk, model=Cylinder(resolution=6), color=warna_lidi, scale=(0.1, 0.9, 0.1), position=(-0.2, 0.45, 0))
    Entity(parent=entiti_induk, model=Cylinder(resolution=6), color=warna_lidi, scale=(0.1, 0.9, 0.1), position=(0.2, 0.45, 0))

# --- 10. FUNC GENERATOR ENTITI UTAMA & MUSUH PULAU ---
def bina_askar_lidi(posisi, indeks):
    askar = Entity(position=posisi, model=muat_mesh_obj_selamat('Askar_Lidi.obj'), scale=(1, 1, 1), color=color.rgb(30, 40, 70), collider='box') 
    askar.nama = f"Askar Lidi {indeks}"; askar.status = "NEUTRAL"; askar.darah = 200; askar.racun_timer = 0
    askar.oksigen = 100.0
    askar.hp_text = Text3D(text=askar.status, parent=askar, y=2.8, billboard=True, scale=0.6, color=color.green)
    senarai_askar.append(askar); daftar_objek_pejal(askar, 1.8)

def bina_musuh_merah(posisi, indeks):
    m = Entity(position=posisi, model=muat_mesh_obj_selamat('Musuh_Merah.obj'), scale=(1, 1, 1), color=color.red, collider='box') 
    m.nama = f"Musuh Merah {indeks}"; m.darah = 60; m.status = "IDLE"; m.is_ketua = False; m.racun_timer = 0
    m.oksigen = 100.0
    pasang_tangan_kaki_normal(m, color.red)
    m.hp_text = Text3D(text=f"HP: {int(m.darah)}", parent=m, y=2.8, billboard=True, scale=0.6, color=color.red)
    senarai_musuh.append(m); daftar_objek_pejal(m, 1.8)

def bina_musuh_pulau(posisi, indeks):
    pahlawan = Entity(position=posisi, model=muat_mesh_obj_selamat('Musuh_Merah.obj'), scale=(1.2, 1.2, 1.2), color=color.rgb(200, 100, 20), collider='box')
    pahlawan.nama = f"Pahlawan Pulau #{indeks}"
    pahlawan.darah = 250
    pahlawan.status = "PATROL"
    pahlawan.is_musuh_pulau = True
    pahlawan.is_ketua_pulau = False
    pahlawan.is_ketua = False
    pahlawan.racun_timer = 0
    pahlawan.oksigen = 100.0
    
    pahlawan.vy = 0
    pahlawan.pemasa_lompat = random.uniform(1.0, 3.0)
    pahlawan.pemasa_serang = random.uniform(1.0, 2.0)
    pahlawan.perisai_aktif = True
    
    pahlawan.perisai = Entity(parent=pahlawan, model='cube', color=color.gold, scale=(0.5, 1.0, 0.1), position=(-0.5, 1.0, 0.3))
    pahlawan.lembing_visual = Entity(parent=pahlawan, model='cylinder', color=color.rgb(139, 69, 19), scale=(0.06, 2.2, 0.06), position=(0.5, 1.0, 0.2), rotation_x=80)
    
    pasang_tangan_kaki_normal(pahlawan, color.rgb(200, 100, 20))
    pahlawan.hp_text = Text3D(text=f"{pahlawan.nama}\nHP: {int(pahlawan.darah)}", parent=pahlawan, y=3.2, billboard=True, scale=0.6, color=color.orange)
    
    senarai_musuh_pulau.append(pahlawan)
    senarai_musuh.append(pahlawan)
    daftar_objek_pejal(pahlawan, 2.0)

def bina_ketua_pulau(posisi):
    ketua = Entity(position=posisi, model=muat_mesh_obj_selamat('Ketua_Musuh.obj'), scale=(1.7, 1.7, 1.7), color=color.rgb(140, 20, 20), collider='box')
    ketua.nama = "Ketua Pahlawan Pulau (Scythe)"
    ketua.darah = 800
    ketua.status = "PATROL"
    ketua.is_musuh_pulau = True
    ketua.is_ketua_pulau = True 
    ketua.is_ketua = True
    ketua.racun_timer = 0
    ketua.oksigen = 100.0 
    
    ketua.vy = 0
    ketua.pemasa_lompat = random.uniform(0.8, 2.0)
    ketua.pemasa_serang = random.uniform(0.5, 1.2)
    ketua.perisai_aktif = True
    
    ketua.perisai = Entity(parent=ketua, model='cube', color=color.gold, scale=(0.7, 1.3, 0.12), position=(-0.6, 1.1, 0.3))
    ketua.scythe_pemegang = Entity(parent=ketua, model='cylinder', color=color.rgb(80, 40, 10), scale=(0.07, 2.8, 0.07), position=(0.6, 1.2, 0.2), rotation_x=70)
    ketua.scythe_bilah = Entity(parent=ketua.scythe_pemegang, model='cube', color=color.light_gray, scale=(1.2, 0.1, 0.3), position=(0.5, 1.3, 0), rotation_z=-45)

    pasang_tangan_kaki_normal(ketua, color.rgb(140, 20, 20))
    ketua.hp_text = Text3D(text=f"笞KETUA PULAU 笞能nHP: {int(ketua.darah)}", parent=ketua, y=4.0, billboard=True, scale=0.8, color=color.yellow)
    
    senarai_musuh_pulau.append(ketua)
    senarai_musuh.append(ketua)
    daftar_objek_pejal(ketua, 2.8)

def bina_raksasa_laut(posisi):
    rl = Entity(position=posisi, model='cube', scale=(6, 4, 10), color=color.rgb(0, 50, 120), collider='box')
    rl.nama = "Raksasa Laut Pelindung"
    rl.darah = 1500
    rl.status = "PATROL_LAUT"
    rl.is_raksasa_laut = True
    rl.is_ketua = True
    rl.racun_timer = 0
    rl.kelajuan = 10
    
    Entity(parent=rl, model='cube', color=color.rgb(0, 20, 80), scale=(0.3, 2.5, 3), position=(0, 2.5, 0), rotation_x=30)
    
    rl.hp_text = Text3D(text=f"穴 {rl.nama.upper()} 穴\nHP: {int(rl.darah)}", parent=rl, y=4.5, billboard=True, scale=0.9, color=color.cyan)
    senarai_musuh.append(rl)
    daftar_objek_pejal(rl, 6.0)

def bina_ketua_musuh(posisi, indeks_kelompok):
    ketua = Entity(position=posisi, model=muat_mesh_obj_selamat('Ketua_Musuh.obj'), scale=(1.5, 1.5, 1.5), color=color.rgb(130, 0, 0), collider='box') 
    ketua.nama = f"Ketua Musuh {indeks_kelompok}"; ketua.darah = 180; ketua.status = "IDLE"; ketua.is_ketua = True; ketua.racun_timer = 0
    ketua.oksigen = 100.0
    pasang_tangan_kaki_normal(ketua, color.rgb(130, 0, 0))
    ketua.hp_text = Text3D(text=f"BOSS HP: {int(ketua.darah)}", parent=ketua, y=3.5, billboard=True, scale=0.8, color=color.yellow)
    senarai_musuh.append(ketua); daftar_objek_pejal(ketua, 2.5)

def bina_raksasa(posisi):
    raksasa = Entity(position=posisi, model='cube', scale=(3, 5, 3), color=color.rgb(70, 0, 70), collider='box')
    raksasa.nama = "Raksasa Gergasi"
    raksasa.darah = 800
    raksasa.status = "IDLE"
    raksasa.racun_timer = 0
    raksasa.oksigen = 100.0
    raksasa.is_ketua = True
    raksasa.kelajuan_raksasa = 3
    pasang_tangan_kaki_normal(raksasa, color.rgb(40, 0, 40))
    
    raksasa.hp_text = Text3D(text=f"RAKSASA HP: {int(raksasa.darah)}", parent=raksasa, y=3.5, billboard=True, scale=0.9, color=color.magenta)
    senarai_musuh.append(raksasa)
    daftar_objek_pejal(raksasa, 4.0)

senarai_catapult = []
def bina_catapult(posisi):
    mesin = Entity(position=posisi, model='cube', scale=(4, 3, 5), color=color.orange, collider='box')
    mesin.nama = "Catapult Musuh"
    mesin.darah = 150
    mesin.cooldown_tembak = 5.0 
    mesin.oksigen = 100.0
    
    Entity(parent=mesin, model=Cylinder(resolution=12), scale=(1.2, 0.2, 1.2), position=(-0.6, -0.4, 0.4), rotation_z=90, color=color.black)
    Entity(parent=mesin, model=Cylinder(resolution=12), scale=(1.2, 0.2, 1.2), position=(0.6, -0.4, 0.4), rotation_z=90, color=color.black)
    Entity(parent=mesin, model='cube', scale=(0.2, 4, 0.2), position=(0, 1, 0), rotation_x=45, color=color.brown)
    
    mesin.hp_text = Text3D(text=f"CATAPULT", parent=mesin, y=2, billboard=True, scale=0.6, color=color.red)
    senarai_catapult.append(mesin)
    daftar_objek_pejal(mesin, 3.5)

def bina_musuh_glitch(posisi, tahap):
    skala_faktor = 1.0 + (tahap * 0.25)
    g = Entity(position=posisi, model=None, scale=(skala_faktor, skala_faktor, skala_faktor), collider='box')
    g.is_glitch = True; g.glitch_tier = tahap; g.status = "IDLE"; g.racun_timer = 0; g.is_ketua = False
    g.nama = f"Glitch Tahap {tahap}"
    
    if tahap == 1:
        g.darah = 120; g.glitch_damage = 25; warna_glitch = color.lime
        pasang_badan_lidi_glitch(g, warna_glitch, tahap)
    elif tahap == 2:
        g.darah = 280; g.glitch_damage = 55; warna_glitch = color.magenta
        pasang_badan_lidi_glitch(g, warna_glitch, tahap)
    elif tahap == 3:
        g.darah = 600; g.glitch_damage = 95; warna_glitch = color.black
        pasang_badan_lidi_glitch(g, warna_glitch, tahap)
    elif tahap == 4:
        g.darah = 1000; g.glitch_damage = 120; warna_glitch = color.orange
        pasang_badan_lidi_glitch(g, warna_glitch, tahap)
    elif tahap == 5:
        g.darah = 2000; g.glitch_damage = 180
        g.model = 'cube'; g.scale_y = 2; g.color = color.rgb(0, 50, 0)
        for i in range(3):
            Text3D(text="ERROR", parent=g, y=0.5 + (i*0.6), z=-0.1, color=color.green, scale=0.8, billboard=True)
    elif tahap == 6:
        g.darah = 9999; g.glitch_damage = 25 
        kepala = Entity(parent=g, model='sphere', color=color.blue, scale=(0.7, 0.7, 0.7), position=(0, 1.8, 0))
        Text3D(text=":(", parent=kepala, position=(-0.1, 0.1, -0.4), scale=1.2, color=color.white)
        
        Text3D(text="BSOD", parent=g, color=color.white, scale=0.9, position=(0, 1.2, 0), billboard=True)
        Text3D(text="BSOD", parent=g, color=color.blue, scale=0.7, position=(-0.5, 1.0, 0), billboard=True)
        Text3D(text="BSOD", parent=g, color=color.blue, scale=0.7, position=(0.5, 1.0, 0), billboard=True)
        Text3D(text="BSOD", parent=g, color=color.dark_gray, scale=0.6, position=(-0.3, 0.4, 0), billboard=True)
        Text3D(text="BSOD", parent=g, color=color.dark_gray, scale=0.6, position=(0.2, 0.4, 0), billboard=True)

    g.hp_text = Text3D(text=f"GLITCH T{tahap}: {int(g.darah)}", parent=g, y=3.2, billboard=True, scale=0.7, color=color.red if tahap >= 4 else color.yellow)
    senarai_musuh.append(g); daftar_objek_pejal(g, 2.0 * skala_faktor)

def musuh_glitch_serang_pemain(musuh_tier):
    global skrin_bsod_palsu
    if pemain.cooldown_diserang > 0: return 

    if musuh_tier == 4:
        pemain.darah -= 40
        pemain.cooldown_diserang = 1.0
    elif musuh_tier == 5:
        pemain.darah -= 60
        pemain.cooldown_diserang = 1.5
    elif musuh_tier == 6:
        pemain.cooldown_diserang = 6.0 
        if skrin_bsod_palsu and not skrin_bsod_palsu.enabled:
            skrin_bsod_palsu.enabled = True
            pemain.kunci_bsod = True
            pemain.kunci_gerak_bsod = {
                'w': held_keys['w'], 
                'a': held_keys['a'], 
                's': held_keys['s'], 
                'd': held_keys['d']
            }
            invoke(hilangkan_bsod, delay=5)

def bina_pemanah(posisi, is_musuh=False):
    p = Entity(position=posisi, model=muat_mesh_obj_selamat('Askar_Lidi.obj'), scale=(1, 1, 1), collider='box') 
    p.color = color.red if is_musuh else color.rgb(30, 80, 30)
    p.nama = "Pemanah Musuh" if is_musuh else "Pemanah Lidi"
    p.cooldown_memanah = 0; p.racun_timer = 0; p.is_musuh = is_musuh 
    p.oksigen = 100.0
    p.hp_text = Text3D(text=p.nama.upper(), parent=p, y=2.8, billboard=True, scale=0.6, color=color.red if is_musuh else color.green)
    senarai_pemanah.append(p)

npc_kampung_count = 1

def bina_npc_kampung(posisi):
    global npc_kampung_count
    npc = Entity(position=posisi, model=muat_mesh_obj_selamat('NPC_Kampung.obj'), scale=(1, 1, 1), color=color.rgb(225, 190, 130), collider='box') 
    npc.nama = f"Orang Kampung {npc_kampung_count}"; npc.dialog = f"{npc.nama}: Sila jangan cetus kekacauan di sini."
    npc.darah_maksimum = 50; npc.darah = 50; npc.is_npc_campung = True; npc.sudah_melapor = False; npc.racun_timer = 0
    npc.oksigen = 100.0
    npc.status = "AMAN"; npc.penyerang = None; npc.kelajuan = 10 
    pasang_tangan_kaki_normal(npc, color.rgb(225, 190, 130))
    npc.hp_text = Text3D(text=npc.nama, parent=npc, y=2.8, billboard=True, scale=0.5, color=color.white)
    senarai_npc.append(npc); daftar_objek_pejal(npc, 1.5)
    npc_kampung_count += 1
    
# --- 10. KUBU, BANGUNAN KOTA & PENJARA PULAU ---
def bina_penjara_pulau_misteri(posisi):
    px, py, pz = posisi
    Entity(model='plane', color=color.dark_gray, scale=(20, 1, 20), position=(px, py + 0.1, pz), collider='box')
    Entity(model='cube', color=color.black, scale=(20, 10, 1), position=(px, py + 5, pz + 10), collider='box')
    Entity(model='cube', color=color.black, scale=(20, 10, 1), position=(px, py + 5, pz - 10), collider='box')
    Entity(model='cube', color=color.black, scale=(1, 10, 20), position=(px - 10, py + 5, pz), collider='box')

    pintu_besi = Entity(model='cube', color=color.rgb(80, 20, 20), scale=(1, 10, 10), position=(px + 10, py + 5, pz), collider='box')
    pintu_besi.darah = 120
    pintu_besi.is_pintu_penjara_pulau = True
    pintu_besi.hp_text = Text3D(text="PINTU PENJARA PULAU\n(KETUK SENJATA UNTUK PECAH!)", parent=pintu_besi, y=6, scale=0.8, color=color.red)
    senarai_musuh.append(pintu_besi)
    daftar_objek_pejal(pintu_besi, 2.0)

def bina_kubu_realistik(pusat, indeks_kelompok):
    px, py, pz = pusat; c_batu = color.gray; c_atap = color.dark_gray       
    Entity(model='cube', color=color.gray, scale=(28, 0.1, 28), position=(px, py + 0.1, pz))
    
    blok_kubu = Entity(model='cube', color=c_batu, scale=(15, 12, 15), position=(px, py + 6, pz))
    daftar_objek_pejal(blok_kubu, 8.0)
    penjuru_menara = [(-11, -11), (11, -11), (-11, 11), (11, 11)]
    for tx, tz in penjuru_menara:
        Entity(model='cube', color=c_batu, scale=(2.5, 18, 2.5), position=(px + tx, py + 9, pz + tz))
        Entity(model='sphere', color=c_atap, scale=(3, 2, 3), position=(px + tx, py + 18, pz + tz))
    pintu_gerbang = Pintu(position=(px, py + 2.5, pz - 11), scale=(6, 5, 0.2), rotation_y=0)
    pintu_gerbang.hitbox_asal = 1.5
    senarai_pintu.append(pintu_gerbang); daftar_objek_pejal(pintu_gerbang, 1.5)

def bina_kubu_pemain(pusat):
    px, py, pz = pusat; c_batu = color.rgb(60, 70, 90)     
    Entity(model='cube', color=color.gray, scale=(36, 0.1, 36), position=(px, py + 0.1, pz))
    
    blok_kubu = Entity(model='cube', color=c_batu, scale=(30, 20, 30), position=(px, py + 10, pz))
    daftar_objek_pejal(blok_kubu, 16.0)
    penjuru_menara = [(-15, -15), (15, -15), (-15, 15), (15, 15)]
    for tx, tz in penjuru_menara:
        Entity(model='cube', color=c_batu, scale=(5, 30, 5), position=(px + tx, py + 15, pz + tz))
        Entity(model='sphere', color=color.gold, scale=(6, 3, 6), position=(px + tx, py + 30, pz + tz))
    pintu_pemain = Pintu(position=(px, py + 3, pz - 15.1), scale=(8, 6, 0.4), rotation_y=0, color=color.gray)
    pintu_pemain.hitbox_asal = 2.0
    senarai_pintu.append(pintu_pemain); daftar_objek_pejal(pintu_pemain, 2.0)  

def bina_rumah(posisi, c_dinding, c_bumbung):
    px, py, pz = posisi
    dinding = Entity(model='cube', color=c_dinding, scale=(6, 10, 6), position=(px, py + 5, pz))
    daftar_objek_pejal(dinding, 4.0) 
    Entity(model='cube', color=c_bumbung, scale=(6.5, 1.5, 6.5), position=(px, py + 10.75, pz))

def bina_perkampungan(pusat, jejari_min, jejari_max, jumlah_rumah, c_dinding, c_bumbung, is_musuh=False):
    px, py, pz = pusat
    jejari_dinding = jejari_max + 8
    
    Entity(model=Cylinder(resolution=24), color=color.gray, scale=((jejari_dinding + 4) * 2, 0.1, (jejari_dinding + 4) * 2), position=(px, py + 0.05, pz))

    for _ in range(jumlah_rumah):
        sudut = random.uniform(0, math.pi * 2); jarak = random.uniform(jejari_min, jejari_max - 5) 
        pos_x = px + math.cos(sudut) * jarak; pos_z = pz + math.sin(sudut) * jarak
        bina_rumah((pos_x, py, pos_z), c_dinding, c_bumbung)
        if not is_musuh: bina_npc_kampung((pos_x + random.uniform(-4, 4), py, pos_z + 4))
        
    jumlah_tembok = 24 
    for i in range(jumlah_tembok):
        sudut_rad = math.radians(i * (360 / jumlah_tembok))
        tembok_x = px + math.cos(sudut_rad) * jejari_dinding
        tembok_z = pz + math.sin(sudut_rad) * jejari_dinding
        lebar_tembok = (jejari_dinding * 2 * math.pi) / jumlah_tembok + 2
        rotasi_tembok = -math.degrees(sudut_rad) + 90
        
        if i == 0:
            gerbang_atas = Entity(model='cube', color=color.rgb(70, 70, 70), scale=(lebar_tembok, 4, 3), position=(tembok_x, py + 10, tembok_z))
            gerbang_atas.rotation_y = rotasi_tembok
            offset_x = math.cos(sudut_rad + math.pi/2) * (lebar_tembok / 2 - 1.5)
            offset_z = math.sin(sudut_rad + math.pi/2) * (lebar_tembok / 2 - 1.5)
            tiang_1 = Entity(model='cube', color=color.rgb(90, 90, 90), scale=(3, 12, 3), position=(tembok_x + offset_x, py + 6, tembok_z + offset_z))
            tiang_2 = Entity(model='cube', color=color.rgb(90, 90, 90), scale=(3, 12, 3), position=(tembok_x - offset_x, py + 6, tembok_z - offset_z))
            tiang_1.rotation_y = rotasi_tembok; tiang_2.rotation_y = rotasi_tembok
            daftar_objek_pejal(tiang_1, 1.5); daftar_objek_pejal(tiang_2, 1.5)
            bina_pemanah((tembok_x, py + 13, tembok_z), is_musuh)
        else:
            tembok = Entity(model='cube', color=color.rgb(90, 90, 90), scale=(lebar_tembok, 12, 3), position=(tembok_x, py + 6, tembok_z))
            tembok.rotation_y = rotasi_tembok
            daftar_objek_pejal(tembok, lebar_tembok / 2) 
            if i % 4 == 0: bina_pemanah((tembok_x, py + 13, tembok_z), is_musuh)

dunia_sudah_dijana = False

def jana_seluruh_dunia():
    global dunia_sudah_dijana
    if dunia_sudah_dijana: return
    
    dunia_sudah_dijana = True 
    
    if 'butang_bahasa' in globals():
        teks_dialog.text = "Sistem: Sedang menjana dunia..." if "Language: Malay" in butang_bahasa.text else "System: Generating world..."
            
    bina_kubu_pemain((0, 0, 0))
    bina_perkampungan((0, 0, 0), 35, 60, 5, color.rgb(200, 180, 150), color.rgb(139, 69, 19))

    posisi_askar = [(0,0,16), (10,0,20), (-10,0,20), (30,0,-10), (-30,0,-10)]
    for idx, pos in enumerate(posisi_askar, start=1): 
        bina_askar_lidi(pos, idx)

    pusat_kelompok = [(150, 0, 150), (-180, 0, 220)]
    for i, pusat in enumerate(pusat_kelompok):
        bina_kubu_realistik(pusat, i + 1)
        bina_perkampungan(pusat, 22, 40, 3, color.rgb(60, 60, 60), color.rgb(20, 20, 20), True)
        bina_ketua_musuh((pusat[0], pusat[1], pusat[2] + 2), i + 1)
        for k in range(4): 
            bina_musuh_merah((pusat[0] + random.uniform(-15, 15), 0, pusat[2] + random.uniform(-15, 5)), i*10 + k)

    pusat_pulau = (1800, 0, 1800)
    bina_perkampungan(pusat_pulau, 40, 120, 15, color.rgb(100, 50, 20), color.rgb(180, 80, 0), True)
    bina_penjara_pulau_misteri((1820, 0, 1820))
    bina_ketua_pulau((1800, 0, 1800))

    for idx in range(1, 51):
        pos_x = 1800 + random.uniform(-180, 180)
        pos_z = 1800 + random.uniform(-180, 180)
        bina_musuh_pulau((pos_x, 0, pos_z), idx)

    bina_raksasa_laut((2200, -1, 1800))
    bina_raksasa_laut((1400, -1, 1800))

    bina_musuh_glitch((40, 0, 40), 1)
    bina_musuh_glitch((60, 0, 60), 2)
    bina_musuh_glitch((80, 0, 80), 3)
    bina_musuh_glitch((100, 0, 100), 4)
    bina_musuh_glitch((120, 0, 120), 5)
    bina_musuh_glitch((140, 0, 140), 6) 
        
    bina_raksasa((120, 0, 180))
    bina_catapult((140, 0, 160))
    bina_catapult((-150, 0, 190))

    if 'butang_bahasa' in globals():
        teks_dialog.text = "Sistem: Dunia berjaya dijana!" if "Language: Malay" in butang_bahasa.text else "System: World fully generated!"

# --- 11. NETWORK SOCKETS ---
def kendalikan_klien(conn, addr):
    while True:
        try:
            data = conn.recv(1024).decode('utf-8')
            if not data: break
            for client in senarai_client:
                if client != conn:
                    try: client.send(data.encode('utf-8'))
                    except Exception: pass
        except Exception:
            break
    if conn in senarai_client:
        senarai_client.remove(conn)
    conn.close()

def jalankan_server():
    global soket_server, senarai_client
    try:
        soket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soket_server.bind((HOST_IP, PORT))
        soket_server.listen()
        while True:
            conn, addr = soket_server.accept()
            if len(senarai_client) < MAX_PEMAIN: 
                senarai_client.append(conn)
                threading.Thread(target=kendalikan_klien, args=(conn, addr), daemon=True).start()
            else: 
                conn.send("PENUH".encode('utf-8'))
                conn.close()
    except Exception as e:
        print(f"Ralat Server: {e}")

def dengar_arahan_server():
    global status_rangkaian
    while True:
        try:
            mesej = soket_client.recv(1024).decode('utf-8')
            if mesej == "MULA_GAME": status_rangkaian = "MULA"
            elif mesej == "PENUH": status_rangkaian = "PENUH"; break
        except Exception: break

# --- 12. HUD & INTERFAS ---
hud_game = Entity(parent=camera.ui, enabled=False)
bingkai_profil = Entity(parent=hud_game, model='circle', color=color.dark_gray, scale=(0.14, 0.14), position=(-0.82, 0.42))
potret = Entity(parent=bingkai_profil, model='circle', color=color.gray, scale=(0.9, 0.9), z=-0.1)
teks_level = Text(parent=hud_game, text="Lv.1", position=(-0.855, 0.435), scale=1.3, color=color.yellow, z=-1)
bar_hp = HealthBar(parent=hud_game, max_value=pemain.darah_maksimum, value=pemain.darah, bar_color=color.red, roundness=0, scale=(0.3, 0.03), position=(-0.65, 0.45))
teks_hp_nombor = Text(parent=hud_game, text="", origin=(0,0), scale=1, color=color.white, position=(-0.65, 0.445), z=-2)

bar_sanity = HealthBar(parent=hud_game, max_value=pemain.sanity_maksimum, value=pemain.sanity, bar_color=color.magenta, roundness=0, scale=(0.3, 0.03), position=(-0.65, 0.41))
teks_sanity_nombor = Text(parent=hud_game, text="", origin=(0,0), scale=1, color=color.white, position=(-0.65, 0.405), z=-2)
overlay_halusinasi = Entity(parent=camera.ui, model='quad', color=color.rgba(100, 0, 150, 0), scale=(2, 2), enabled=False, z=-5)

kotak_senjata = Button(parent=hud_game, text=pemain.slot_senjata, color=color.rgba(0,0,0,0.6), text_color=color.white, scale=(0.14, 0.035), position=(-0.74, 0.38))
kotak_syiling = Button(parent=hud_game, text=pemain.slot_syiling, color=color.rgba(0,0,0,0.6), text_color=color.white, scale=(0.14, 0.035), position=(-0.59, 0.38))

bg_dialog = Entity(parent=hud_game, model='quad', color=color.rgba(0,0,0,0.6), scale=(0.8, 0.08), position=(0, -0.38))
teks_dialog = Text(parent=hud_game, text='Sistem: Klik Kiri menyerang. SPACEBAR untuk Dash. Tekan E interaksi. Tekan TAB buka Inventori.', position=(0, -0.38), origin=(0, 0), scale=1.3, color=color.white)
teks_status_askar = Text(parent=hud_game, text='Status Askar: AMAN / PATROL', position=(0, 0.45), origin=(0, 0), scale=1.5, color=color.green)
teks_oksigen = Text(parent=hud_game, text="", position=(0, -0.25), origin=(0, 0), scale=1.5, color=color.cyan)

skrin_inventori = Entity(parent=camera.ui, enabled=False, z=-1)
Entity(parent=skrin_inventori, model='quad', color=color.rgba(0, 0, 0, 0.9), scale=(1.2, 0.9))
Text(parent=skrin_inventori, text="INVENTORI PEMAIN", origin=(0, 0), scale=2.5, color=color.yellow, y=0.35)
Text(parent=skrin_inventori, text="(Klik butang untuk guna/equip. Tekan TAB untuk tutup)", origin=(0, 0), scale=1, color=color.white, y=0.28)
senarai_butang_inv = []

def kemas_kini_inventori():
    for b in senarai_butang_inv: destroy(b)
    senarai_butang_inv.clear()
    for i, item in enumerate(pemain.inventori):
        pos_y = 0.15 - (i * 0.08)
        b = Button(parent=skrin_inventori, text=item, scale=(0.4, 0.06), position=(0, pos_y), color=color.dark_gray)
        def equip_item(nama_item=item):
            if nama_item in senjata_stats:
                pemain.slot_senjata = nama_item; kotak_senjata.text = nama_item
                bina_model_senjata(nama_item, pemain.model_senjata)
                teks_dialog.text = f"Sistem: Senjata dilengkapkan: [{nama_item}]" if "Language: Malay" in butang_bahasa.text else f"System: Weapon equipped: [{nama_item}]"
            elif nama_item == "Alatan Ubatan":
                pemain.darah = min(pemain.darah_maksimum, pemain.darah + 50)
                pemain.sanity = min(pemain.sanity_maksimum, pemain.sanity + 50)
                if "Alatan Ubatan" in pemain.inventori: pemain.inventori.remove("Alatan Ubatan")
                teks_dialog.text = "Sistem: Nyawa dan Sanity dipulihkan!" if "Language: Malay" in butang_bahasa.text else "System: Health and Sanity restored!"
                kemas_kini_inventori() 
            elif nama_item == "Roti":
                pemain.sanity = min(pemain.sanity_maksimum, pemain.sanity + 20) 
                pemain.darah = min(pemain.darah_maksimum, pemain.darah + 10)    
                if "Roti" in pemain.inventori: pemain.inventori.remove("Roti")
                teks_dialog.text = "Sistem: Anda makan Roti!" if "Language: Malay" in butang_bahasa.text else "System: You ate Bread!"
                kemas_kini_inventori()
            elif nama_item == "Air Minuman":
                pemain.sanity = min(pemain.sanity_maksimum, pemain.sanity + 35) 
                if "Air Minuman" in pemain.inventori: pemain.inventori.remove("Air Minuman")
                teks_dialog.text = "Sistem: Anda minum air!" if "Language: Malay" in butang_bahasa.text else "System: You drank water!"
                kemas_kini_inventori()
        b.on_click = equip_item; senarai_butang_inv.append(b)

skrin_penjara = Entity(parent=camera.ui, enabled=False)
Entity(parent=skrin_penjara, model='quad', color=color.rgba(50, 0, 0, 0.75), scale=(2, 2))
Text(parent=skrin_penjara, text="ANDA DITANGKAP ASKAR LIDI!", origin=(0,0), scale=3, color=color.red, y=0.2)
Text(parent=skrin_penjara, text="Kesalahan: Menceroboh / Menyerang Orang Awam", origin=(0,0), scale=1.3, color=color.white, y=0.1)
teks_pemasa_penjara = Text(parent=skrin_penjara, text="Sisa Hukuman: 60s", origin=(0,0), scale=2.5, color=color.yellow, y=-0.05)

menu_pause_panel = Entity(parent=camera.ui, enabled=False, z=-2)
Entity(parent=menu_pause_panel, model='quad', color=color.rgba(0, 0, 0, 0.85), scale=(2, 2))
Text(parent=menu_pause_panel, text="PERMAINAN DIHENTIKAN", origin=(0,0), scale=3, color=color.yellow, y=0.15)

def fungsi_buka_tutup_pause():
    global game_berjalan
    if not pemain_hidup or pemain.dalam_penjara or skrin_inventori.enabled: return 
    game_berjalan = not game_berjalan
    menu_pause_panel.enabled = not game_berjalan
    mouse.locked = game_berjalan; mouse.visible = not game_berjalan

def buka_main_menu():
    global game_berjalan
    game_berjalan = False
    menu_pause_panel.enabled = False
    hud_game.enabled = False
    skrin_inventori.enabled = False
    skrin_mati.enabled = False
    skrin_penjara.enabled = False
    skrin_credits.enabled = False
    if 'skrin_tetapan' in globals(): skrin_tetapan.enabled = False
    menu_pilih_mod.enabled = False
    menu_multiplayer.enabled = False
    menu_lobi_host.enabled = False
    menu_lobi_client.enabled = False
    
    main_menu.enabled = True
    mouse.locked = False
    mouse.visible = True
    mainkan_lagu_menu()

Button(parent=menu_pause_panel, text="Resume Game", scale=(0.3, 0.07), position=(0, 0.0), color=color.dark_gray, on_click=fungsi_buka_tutup_pause)
Button(parent=menu_pause_panel, text="Quit to Main Menu", scale=(0.3, 0.07), position=(0, -0.1), color=color.dark_gray, on_click=buka_main_menu)

skrin_mati = Entity(parent=camera.ui, enabled=False)
Entity(parent=skrin_mati, model='quad', color=color.rgba(0,0,0,0.9), scale=(2, 2))
Text(parent=skrin_mati, text="KAMU TEWAS", origin=(0,0), scale=4, color=color.red, y=0.2)

skrin_bsod_palsu = Entity(parent=camera.ui, model='quad', color=color.blue, scale=(2, 2), enabled=False, z=-10)
Text(
    parent=skrin_bsod_palsu, 
    text=":( \n\nAMARAN: INI ADALAH BSOD PALSU!\n\nPunca: Glitch Tahap 6\nStatus: Anda sedang kehilangan 13 HP / saat!\n\nJangan lepas butang W, A, S, atau D!", 
    position=(-0.7, 0.3), 
    scale=1.5, 
    color=color.white
)

def fungsi_respawn():
    global pemain_hidup, game_berjalan, global_penceroboh, pemain_diburu_pulau
    pemain_hidup = True; game_berjalan = True; pemain.darah = pemain.darah_maksimum; pemain.position = (0, 0, -20) 
    pemain_diburu_pulau = False
    
    pemain.sanity = pemain.sanity_maksimum
    pemain.oksigen = pemain.oksigen_maksimum
    teks_oksigen.text = ""
    camera.rotation_z = 0
    overlay_halusinasi.enabled = False
    
    skrin_mati.enabled = False; skrin_penjara.enabled = False; menu_pause_panel.enabled = False; hud_game.enabled = True
    skrin_inventori.enabled = False; pemain.dalam_penjara = False; global_penceroboh = None
    
    hilangkan_bsod() 
    
    teks_status_askar.text = "Status Askar: AMAN / PATROL" if "Language: Malay" in butang_bahasa.text else "Guard Status: PEACEFUL / PATROL"
    teks_status_askar.color = color.green
        
    for askar in senarai_askar: askar.status = "NEUTRAL"
    for npc in senarai_npc:
        if getattr(npc, 'is_npc_campung', False):
            npc.status = "AMAN"; npc.sudah_melapor = False
            npc.hp_text.text = npc.nama; npc.hp_text.color = color.white
    for mp in senarai_musuh_pulau: mp.status = "PATROL"
    mouse.locked = True; mouse.visible = False

Button(parent=skrin_mati, text="Respawn", scale=(0.3, 0.08), position=(0, -0.05), color=color.dark_gray, on_click=fungsi_respawn)

# --- 13. MENU UTAMA & MULTIPLAYER ---
main_menu = Entity(parent=camera.ui, enabled=True)
Text(parent=main_menu, text="PERANG LIDI", origin=(0,0), scale=4, color=color.yellow, y=0.3)

menu_pilih_mod = Entity(parent=camera.ui, enabled=False)
Entity(parent=menu_pilih_mod, model='quad', color=color.rgba(0, 0, 0, 0.9), scale=(2, 2))
teks_tajuk_mod = Text(parent=menu_pilih_mod, text="PILIH MOD PERMAINAN", origin=(0,0), scale=3, color=color.yellow, y=0.25)

def buka_pilih_mod():
    main_menu.enabled = False
    menu_pilih_mod.enabled = True

def pilih_singleplayer():
    menu_pilih_mod.enabled = False
    mula_permainan_single()

def pilih_multiplayer():
    menu_pilih_mod.enabled = False
    menu_multiplayer.enabled = True

def kembali_ke_main_menu():
    menu_pilih_mod.enabled = False
    main_menu.enabled = True

butang_single = Button(parent=menu_pilih_mod, text="Singleplayer (Luar Talian)", scale=(0.4, 0.07), position=(0, 0.08), color=color.green, on_click=pilih_singleplayer)
butang_multi = Button(parent=menu_pilih_mod, text="Multiplayer (Atas Talian)", scale=(0.4, 0.07), position=(0, -0.02), color=color.rgb(180, 40, 40), on_click=pilih_multiplayer)
butang_kembali_mod = Button(parent=menu_pilih_mod, text="Kembali", scale=(0.4, 0.07), position=(0, -0.12), color=color.gray, on_click=kembali_ke_main_menu)

butang_mula = Button(parent=main_menu, text="Main Permainan", scale=(0.35, 0.07), position=(0, 0.15), color=color.green, on_click=buka_pilih_mod)
butang_tetapan = Button(parent=main_menu, text="Tetapan", scale=(0.35, 0.07), position=(0, 0.05), color=color.orange, on_click=lambda: setattr(skrin_tetapan, 'enabled', True))
butang_credits = Button(parent=main_menu, text="Credits", scale=(0.35, 0.07), position=(0, -0.05), color=color.azure, on_click=lambda: papar_credits())
butang_bahasa = Button(parent=main_menu, text="Language: Malay", scale=(0.35, 0.07), position=(0, -0.15), color=color.blue)
butang_keluar = Button(parent=main_menu, text="Keluar Game", scale=(0.35, 0.07), position=(0, -0.25), color=color.red, on_click=lambda: sys.exit())

skrin_tetapan = Entity(parent=camera.ui, enabled=False, z=-1)
Entity(parent=skrin_tetapan, model='quad', color=color.rgba(0, 0, 0, 0.95), scale=(1.2, 0.8))
Text(parent=skrin_tetapan, text="TETAPAN / SETTINGS", origin=(0, 0), scale=2.2, color=color.yellow, y=0.3)

teks_sens_label = Text(parent=skrin_tetapan, text="Sensitiviti Tetikus:", position=(-0.3, 0.05), scale=1.5, color=color.white)
teks_sens_nilai = Text(parent=skrin_tetapan, text=str(sensitiviti_tetikus), position=(0.15, 0.05), scale=1.5, color=color.yellow)

def ubah_sensitiviti(tambah=True):
    global sensitiviti_tetikus
    sensitiviti_tetikus = min(400, sensitiviti_tetikus + 25) if tambah else max(25, sensitiviti_tetikus - 25)
    teks_sens_nilai.text = str(sensitiviti_tetikus)

Button(parent=skrin_tetapan, text="-", scale=(0.05, 0.05), position=(0.05, 0.05), on_click=lambda: ubah_sensitiviti(False))
Button(parent=skrin_tetapan, text="+", scale=(0.05, 0.05), position=(0.25, 0.05), on_click=lambda: ubah_sensitiviti(True))
butang_simpan = Button(parent=skrin_tetapan, text="Simpan & Tutup", scale=(0.25, 0.06), position=(0, -0.2), color=color.gray, on_click=lambda: setattr(skrin_tetapan, 'enabled', False))

menu_multiplayer = Entity(parent=camera.ui, enabled=False)
Entity(parent=menu_multiplayer, model='quad', color=color.rgba(0,0,0,0.9), scale=(2,2))
Text(parent=menu_multiplayer, text="MULTIPLAYER MENU", origin=(0,0), scale=3, color=color.orange, y=0.3)

menu_lobi_host = Entity(parent=camera.ui, enabled=False)
Entity(parent=menu_lobi_host, model='quad', color=color.rgba(0,0,0,0.9), scale=(2,2))
Text(parent=menu_lobi_host, text="HOST LOBBY (MENUNGGU PEMAIN)", origin=(0,0), scale=2.5, color=color.green, y=0.3)
senarai_teks_host = Text(parent=menu_lobi_host, text="1. Anda (Host)\n", origin=(0,0), scale=1.5, color=color.white, y=0.1)

menu_lobi_client = Entity(parent=camera.ui, enabled=False)
Entity(parent=menu_lobi_client, model='quad', color=color.rgba(0,0,0,0.9), scale=(2,2))
teks_status_join = Text(parent=menu_lobi_client, text="CUBA UNTUK JOIN SERVER...", origin=(0,0), scale=2, color=color.yellow, y=0.2)

def set_bahasa():
    if butang_bahasa.text == "Language: Malay":
        butang_bahasa.text = "Language: English"
        butang_mula.text = "Play Game"
        butang_tetapan.text = "Settings"
        butang_keluar.text = "Exit Game"
        teks_tajuk_mod.text = "SELECT GAME MODE"
        butang_single.text = "Singleplayer (Offline)"
        butang_multi.text = "Multiplayer (Online)"
        butang_kembali_mod.text = "Back"
        teks_dialog.text = 'System: Left Click to attack. SPACEBAR to Dash. E to interact. TAB to open Inventory.'
    else:
        butang_bahasa.text = "Language: Malay"
        butang_mula.text = "Main Permainan"
        butang_tetapan.text = "Tetapan"
        butang_keluar.text = "Keluar Game"
        teks_tajuk_mod.text = "PILIH MOD PERMAINAN"
        butang_single.text = "Singleplayer (Luar Talian)"
        butang_multi.text = "Multiplayer (Atas Talian)"
        butang_kembali_mod.text = "Kembali"
        teks_dialog.text = 'Sistem: Klik Kiri menyerang. SPACEBAR untuk Dash. Tekan E interaksi. Tekan TAB buka Inventori.'

butang_bahasa.on_click = set_bahasa

skrin_credits = Entity(parent=camera.ui, enabled=False)
Entity(parent=skrin_credits, model='quad', color=color.rgba(0,0,0,0.95), scale=(2,2))
Text(parent=skrin_credits, text="KREDIT PENGATURCARAAN", origin=(0,0), scale=2.5, color=color.yellow, y=0.35)
Text(parent=skrin_credits, text="Developer: [Nama Anda]\nGame Engine: Ursina Engine (Python)\nModel 3D: Prosedural & Primitif\n\nTerima kasih kerana bermain Perang Lidi!", origin=(0,0), scale=1.3, color=color.white, y=0.1)
Button(parent=skrin_credits, text="Kembali", scale=(0.25, 0.08), position=(0, -0.3), color=color.gray, on_click=lambda: (setattr(skrin_credits, 'enabled', False), setattr(main_menu, 'enabled', True)))

def papar_credits():
    main_menu.enabled = False
    skrin_credits.enabled = True

def host_game():
    global status_rangkaian
    menu_multiplayer.enabled = False
    menu_lobi_host.enabled = True
    status_rangkaian = "HOST_LOBBY"
    threading.Thread(target=jalankan_server, daemon=True).start()

def join_game():
    global soket_client, status_rangkaian
    menu_multiplayer.enabled = False
    menu_lobi_client.enabled = True
    status_rangkaian = "JOINING"
    try:
        soket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soket_client.connect((HOST_IP, PORT))
        teks_status_join.text = "BERJAYA JOIN! Menunggu Host mula game..."
        teks_status_join.color = color.green
        threading.Thread(target=dengar_arahan_server, daemon=True).start()
    except Exception:
        teks_status_join.text = f"GAGAL JOIN: Server tidak dijumpai."
        teks_status_join.color = color.red

Button(parent=menu_multiplayer, text="Host Game (Server)", scale=(0.35, 0.07), position=(0, 0.1), color=color.green, on_click=host_game)
Button(parent=menu_multiplayer, text="Join Game (Client)", scale=(0.35, 0.07), position=(0, 0), color=color.blue, on_click=join_game)
Button(parent=menu_multiplayer, text="Kembali", scale=(0.35, 0.07), position=(0, -0.1), color=color.gray, on_click=lambda: (setattr(menu_multiplayer, 'enabled', False), setattr(menu_pilih_mod, 'enabled', True)))

def mula_permainan_single():
    global game_berjalan, pemain_hidup
    main_menu.enabled = False
    hud_game.enabled = True
    hentikan_lagu_menu()
    jana_seluruh_dunia() 
    kemas_kini_inventori()
    pemain_hidup = True
    game_berjalan = True
    mouse.locked = True
    mouse.visible = False
    pemain.position = (0, 0, -20)

def host_mula_game():
    global game_berjalan
    menu_lobi_host.enabled = False
    for client in senarai_client:
        try: client.send("MULA_GAME".encode('utf-8'))
        except Exception: pass
    
    for i in range(len(senarai_client)):
        pm = PemainMultiplayer(posisi_awal=(random.uniform(-10, 10), 0, random.uniform(-10, 10)), nama_pemain=f"Pemain {i+2}")
        senarai_pemain_multiplayer.append(pm)
        
    bina_ui_chat_multiplayer()
    mula_permainan_single()

Button(parent=menu_lobi_host, text="Start Multiplayer", scale=(0.35, 0.08), position=(0, -0.2), color=color.red, on_click=host_mula_game)

# --- 14. SISTEM KAWALAN PEMAIN & INPUT ---
def input(key):
    global game_berjalan, kecepatan_jalan, kotak_input_chat, pemain_diburu_pulau
    if not game_berjalan or not pemain_hidup:
        if key == 'escape' and not skrin_mati.enabled and not skrin_penjara.enabled:
            if not main_menu.enabled and not menu_multiplayer.enabled and not menu_lobi_host.enabled and not menu_lobi_client.enabled and not menu_pilih_mod.enabled:
                fungsi_buka_tutup_pause()
        return

    if key == 'escape':
        fungsi_buka_tutup_pause()

    if key == 'enter' and kotak_input_chat:
        kotak_input_chat.active = not kotak_input_chat.active

    if kotak_input_chat and kotak_input_chat.active:
        return

    if key == 'space':
        if pemain.cooldown_dash <= 0:
            pemain.pemasa_dash = 0.15   
            pemain.cooldown_dash = 1.5  
            teks_dialog.text = "Sistem: DASH!" if "Language: Malay" in butang_bahasa.text else "System: DASH!"

    if key == 'tab':
        if not skrin_inventori.enabled:
            skrin_inventori.enabled = True
            mouse.locked = False
            mouse.visible = True
            kemas_kini_inventori()
        else:
            skrin_inventori.enabled = False
            mouse.locked = True
            mouse.visible = False

    if key == 'left shift':
        kecepatan_jalan = KELAJUAN_SPRINT
    elif key == 'left shift up':
        kecepatan_jalan = KELAJUAN_JALAN

    if key == 'e':
        for pinton in senarai_pintu:
            if distance(pemain.position, pinton.position) < 5.0:
                pinton.toggle()

    if key == 'left mouse down':
        info_senjata = senjata_stats.get(pemain.slot_senjata, senjata_stats["Tangan Kosong"])
        jarak_serang = info_senjata["range"]
        damage_serang = info_senjata["damage"]
        is_beracun = info_senjata["poison"]
        
        if info_senjata["type"] == "ranged":
            teks_dialog.text = "Sistem: Memanah musuh!" if "Language: Malay" in butang_bahasa.text else "System: Shooting arrow!"
            arah_depan = kamera_pivot.forward
            arah_depan.y = 0
            if arah_depan.length() > 0:
                arah_depan = arah_depan.normalized()
            AnakPanahPemain(posisi=pemain.position + Vec3(0, 1.5, 0), arah=arah_depan, damage_panah=damage_serang, beracun=is_beracun)
        else:
            teks_dialog.text = f"Sistem: Menyerang jarak dekat ({damage_serang} DMG)!" if "Language: Malay" in butang_bahasa.text else f"System: Melee attack ({damage_serang} DMG)!"

            for m in senarai_musuh + senarai_npc + senarai_pemanah:
                if m and m.enabled and distance(pemain.position, m.position) < jarak_serang:
                    if getattr(m, 'is_pintu_penjara_pulau', False):
                        m.darah -= damage_serang
                        m.hp_text.text = f"PINTU PENJARA PULAU\nHP: {int(m.darah)}"
                        if m.darah <= 0:
                            m.enabled = False
                            pemain_diburu_pulau = True
                            teks_dialog.text = "AMARAN! 100 PAHLAWAN PULAU & KETUA SCYTHE SEDANG MEMBURU ANDA!" if "Language: Malay" in butang_bahasa.text else "WARNING! 100 ISLAND WARRIORS ARE HUNTING YOU!"
                            for mp in senarai_musuh_pulau:
                                mp.status = "DIBURU"
                        continue

                    if getattr(m, 'status', '') != "DIPENJARA":
                        if hasattr(m, 'darah'):
                            damage_akhir = damage_serang
                            if getattr(m, 'perisai_aktif', False):
                                damage_akhir *= 0.3 if getattr(m, 'is_ketua_pulau', False) else 0.4
                            m.darah -= damage_akhir
                            if is_beracun: m.racun_timer = 5.0
                        
                        if getattr(m, 'is_npc_campung', False) and not m.sudah_melapor:
                            m.status = "LARI_REPOT"
                            m.penyerang = pemain
                            m.hp_text.text = "TOLONG! NAK REPOT ASKAR!"
                            m.hp_text.color = color.orange
                        
                        if getattr(m, 'is_musuh', False) and m in senarai_pemanah:
                            m.status = "DISERANG"
            
            for am in senarai_askar:
                if am and am.enabled and distance(pemain.position, am.position) < jarak_serang:
                    am.darah -= damage_serang
                    am.status = "KEJAR"

# --- FUNGSI UTAMA KEMAS KINI LEMAS & LAUTAN ---
def semak_dan_kemas_kini_lemas(ent):
    if not hasattr(ent, 'darah') or ent.darah <= 0 or not ent.enabled:
        return

    if getattr(ent, 'is_glitch', False) or getattr(ent, 'is_musuh_pulau', False):
        return

    if getattr(ent, 'is_raksasa_laut', False):
        di_darat_benua = (-1500 <= ent.position.x <= 1500 and -1500 <= ent.position.z <= 1500 and not (360 <= ent.position.x <= 440))
        di_darat_pulau = (1400 <= ent.position.x <= 2200 and 1400 <= ent.position.z <= 2200)
        
        if (di_darat_benua or di_darat_pulau) and ent.position.y >= 0:
            ent.darah = 0
            if hasattr(ent, 'hp_text') and ent.hp_text:
                ent.hp_text.text = f"{ent.nama}\n(MATI TERKANDAS DI DARAT!)"
                ent.hp_text.color = color.red
        return

    paras_air = 0.1 if 360 < ent.position.x < 440 else (-1.5 if ent.position.y < -0.5 else None)

    if paras_air is not None:
        if (ent.position.y + 1.2) < paras_air:
            if not hasattr(ent, 'oksigen'): ent.oksigen = 100.0
            ent.oksigen -= 25.0 * time.dt
            if ent.oksigen <= 0:
                ent.oksigen = 0
                ent.darah -= 25.0 * time.dt
                if hasattr(ent, 'hp_text') and ent.hp_text:
                    ent.hp_text.text = f"{getattr(ent, 'nama', 'Musuh')}\n(LEMAS! HP: {int(ent.darah)})"
                    ent.hp_text.color = color.cyan
        else:
            if hasattr(ent, 'oksigen') and ent.oksigen < 100.0:
                ent.oksigen += 30.0 * time.dt

# =============================================================================
# --- 15. MAIN GAME LOOP (UPDATE UTAMA) ---
# =============================================================================
def update():
    global game_berjalan, pemain_hidup, global_penceroboh, status_rangkaian, pemain_diburu_pulau

    if main_menu.enabled and musik_menu is None:
        mainkan_lagu_menu()

    if status_rangkaian == "MULA":
        menu_lobi_client.enabled = False
        status_rangkaian = "BERMAIN"
        mula_permainan_single()

    if not game_berjalan or not pemain_hidup: return
    
    # Pembersihan berkala untuk entiti mati
    pembersihan_entiti_mati()
    kemas_kini_hujan()

    if kotak_input_chat and kotak_input_chat.active: return

    # --- PENGURUSAN MASA PENJARA ---
    if pemain.dalam_penjara:
        pemain.masa_penjara -= time.dt
        if pemain.masa_penjara > 0:
            teks_pemasa_penjara.text = f"Sisa Hukuman: {int(pemain.masa_penjara)}s"
        else:
            pemain.dalam_penjara = False
            skrin_penjara.enabled = False
            hud_game.enabled = True
            pemain.position = (0, 0, -20)
            global_penceroboh = None
            for askar in senarai_askar: askar.status = "NEUTRAL"
        return 

    if skrin_bsod_palsu and skrin_bsod_palsu.enabled:
        pemain.darah -= 13 * time.dt

    # --- UI & STATS UPDATES ---
    bar_hp.value = pemain.darah
    teks_hp_nombor.text = f"{int(pemain.darah)} / {pemain.darah_maksimum}"
    teks_level.text = f"Lv.{pemain.tahap}"

    if pemain.sanity > 0:
        pemain.sanity -= 0.8 * time.dt  
    bar_sanity.value = pemain.sanity
    teks_sanity_nombor.text = f"Sanity: {int(pemain.sanity)} / {pemain.sanity_maksimum}"

    if pemain.sanity <= 0:
        pemain.darah = 0  
    elif pemain.sanity < 10:
        overlay_halusinasi.enabled = True
        overlay_halusinasi.color = color.rgba(150, 0, 200, random.uniform(50, 150))
        camera.rotation_z = random.uniform(-4, 4)
    else:
        if overlay_halusinasi.enabled:
            overlay_halusinasi.enabled = False
            camera.rotation_z = 0

    # --- LOGIK OKSIGEN PEMAIN ---
    paras_air_semasa = 0.1 if 360 < pemain.position.x < 440 else (-1.5 if pemain.position.y < -0.5 else None)
    if paras_air_semasa is not None:
        if (pemain.position.y + 1.5) < paras_air_semasa:
            pemain.oksigen -= 10 * time.dt
            if pemain.oksigen <= 0:
                pemain.oksigen = 0
                pemain.darah -= 20 * time.dt 
                teks_oksigen.text = "AMARAN: ANDA SEDANG LEMAS!"
                teks_oksigen.color = color.red
            else:
                teks_oksigen.text = f"Menyelam... Oksigen: {int(pemain.oksigen)}%"
                teks_oksigen.color = color.cyan
        else:
            if pemain.oksigen < pemain.oksigen_maksimum:
                pemain.oksigen += 25 * time.dt
                teks_oksigen.text = f"Tarik Nafas... {int(pemain.oksigen)}%"
                teks_oksigen.color = color.green
            else:
                teks_oksigen.text = "" 
    else:
        if pemain.oksigen < pemain.oksigen_maksimum:
            pemain.oksigen += 25 * time.dt
            teks_oksigen.text = "" 

    if pemain.darah <= 0:
        pemain_hidup = False
        hud_game.enabled = False
        skrin_mati.enabled = True
        mouse.locked = False
        mouse.visible = True
        return

    if pemain.cooldown_diserang > 0:
        pemain.cooldown_diserang -= time.dt

    # --- MOVEMENT PEMAIN ---
    kamera_pivot.position = pemain.position
    kamera_pivot.rotation_y += mouse.velocity[0] * sensitiviti_tetikus
    camera.rotation_x -= mouse.velocity[1] * sensitiviti_tetikus
    camera.rotation_x = clamp(camera.rotation_x, -20, 80)

    arah_gerak = Vec3(0, 0, 0)
    if pemain.kunci_bsod:
        for k in ['w', 'a', 's', 'd']:
            if not held_keys[k]: pemain.kunci_gerak_bsod[k] = False 
        if pemain.kunci_gerak_bsod['w']: arah_gerak += kamera_pivot.forward
        if pemain.kunci_gerak_bsod['s']: arah_gerak -= kamera_pivot.forward
        if pemain.kunci_gerak_bsod['a']: arah_gerak -= kamera_pivot.right
        if pemain.kunci_gerak_bsod['d']: arah_gerak += kamera_pivot.right
    else:
        if held_keys['w']: arah_gerak += kamera_pivot.forward
        if held_keys['s']: arah_gerak -= kamera_pivot.forward
        if held_keys['a']: arah_gerak -= kamera_pivot.right
        if held_keys['d']: arah_gerak += kamera_pivot.right

    arah_gerak.y = 0

    if pemain.cooldown_dash > 0: pemain.cooldown_dash -= time.dt

    kecepatan_semasa = kecepatan_jalan
    if pemain.pemasa_dash > 0:
        pemain.pemasa_dash -= time.dt
        kecepatan_semasa = KELAJUAN_DASH
        if arah_gerak.length() == 0:
            arah_gerak = kamera_pivot.forward
            arah_gerak.y = 0

    if arah_gerak.length() > 0: arah_gerak = arah_gerak.normalized()

    posisi_baru_x = pemain.position + Vec3(arah_gerak.x, 0, 0) * kecepatan_semasa * time.dt
    posisi_baru_z = pemain.position + Vec3(0, 0, arah_gerak.z) * kecepatan_semasa * time.dt
    
    pelanggaran_x = False; pelanggaran_z = False
    for obj in senarai_objek_pejal:
        if obj and obj.enabled:
            saiz = getattr(obj, 'saiz_pelanggaran', 2.0)
            if distance(posisi_baru_x, obj.position) < saiz: pelanggaran_x = True
            if distance(posisi_baru_z, obj.position) < saiz: pelanggaran_z = True

    if not pelanggaran_x: pemain.x += arah_gerak.x * kecepatan_semasa * time.dt
    if not pelanggaran_z: pemain.z += arah_gerak.z * kecepatan_semasa * time.dt

    if arah_gerak.length() > 0:
        sudut_tuju = math.degrees(math.atan2(arah_gerak.x, arah_gerak.z))
        pemain.rotation_y = lerp_angle(pemain.rotation_y, sudut_tuju, 10 * time.dt)
        pemain.pemasa_animasi += time.dt * kecepatan_semasa * 0.8
        pemain.y = abs(math.sin(pemain.pemasa_animasi)) * 0.25
    else:
        pemain.y = lerp(pemain.y, 0, 10 * time.dt)
        pemain.pemasa_animasi = 0

    if status_rangkaian == "BERMAIN" and soket_client:
        try:
            data_pos = f"POS:{pemain.x},{pemain.y},{pemain.z},{pemain.rotation_y}"
            soket_client.send(data_pos.encode('utf-8'))
        except Exception: pass

    # --- AI: ASKAR LIDI ---
    for askar in senarai_askar:
        if not askar or not askar.enabled: continue
        semak_dan_kemas_kini_lemas(askar)

        if askar.darah <= 0:
            askar.enabled = False
            if hasattr(askar, 'hp_text'): askar.hp_text.enabled = False
            continue

        if distance(pemain.position, askar.position) < 8.0 and pemain.slot_senjata != "Tangan Kosong":
            askar.status = "AMARAN"
        
        if global_penceroboh: askar.status = "KEJAR"

        if askar.status == "AMARAN":
            askar.hp_text.text = "SIMPAN SENJATA!"; askar.hp_text.color = color.orange
            askar.look_at(pemain.position)
            if pemain.slot_senjata == "Tangan Kosong":
                askar.status = "NEUTRAL"; askar.hp_text.text = askar.status; askar.hp_text.color = color.green

        elif askar.status == "KEJAR":
            askar.hp_text.text = "TANGKAP DIA!"; askar.hp_text.color = color.red
            askar.look_at(pemain.position)
            askar.position += askar.forward * kelajuan_askar * time.dt
            if distance(pemain.position, askar.position) < 2.5:
                pemain.dalam_penjara = True
                pemain.masa_penjara = 60
                pemain.position = penjara_pusat + Vec3(0, 5, 0)
                hud_game.enabled = False
                skrin_penjara.enabled = True

    # --- AI: NPC KAMPUNG ---
    for npc in senarai_npc:
        if not npc or not npc.enabled: continue
        semak_dan_kemas_kini_lemas(npc)

        if npc.darah <= 0:
            npc.enabled = False
            if hasattr(npc, 'hp_text'): npc.hp_text.enabled = False
            continue

        if getattr(npc, 'is_npc_campung', False) and npc.status == "LARI_REPOT":
            askar_terdekat = None
            jarak_askar_terdekat = float('inf')
            for askar in senarai_askar:
                if askar and askar.enabled and askar.darah > 0:
                    dist = distance(npc.position, askar.position)
                    if dist < jarak_askar_terdekat:
                        jarak_askar_terdekat = dist
                        askar_terdekat = askar
            
            if askar_terdekat:
                npc.look_at(askar_terdekat.position)
                npc.position += npc.forward * npc.kelajuan * time.dt
                if distance(npc.position, askar_terdekat.position) < 5.0:
                    npc.sudah_melapor = True
                    npc.status = "AMAN"
                    npc.hp_text.text = f"{npc.nama} (Dilaporkan)"; npc.hp_text.color = color.gray
                    global_penceroboh = pemain
            else:
                npc.position += npc.forward * npc.kelajuan * time.dt

    # --- AI: 100 PAHLAWAN PULAU MISTERI & KETUA SCYTHE ---
    for mp in senarai_musuh_pulau:
        if not mp or not mp.enabled: continue
        semak_dan_kemas_kini_lemas(mp)

        if mp.darah <= 0:
            mp.enabled = False; mp.collider = None
            if hasattr(mp, 'hp_text'): mp.hp_text.enabled = False
            continue

        mp.pemasa_lompat -= time.dt
        if mp.y <= 0 and mp.pemasa_lompat <= 0 and (distance(pemain.position, mp.position) < 40.0 or pemain_diburu_pulau):
            mp.vy = 9.5 if getattr(mp, 'is_ketua_pulau', False) else 8.5
            mp.pemasa_lompat = random.uniform(1.5, 3.5)

        mp.y += mp.vy * time.dt
        mp.vy -= 22 * time.dt
        if mp.y < 0: mp.y = 0; mp.vy = 0

        jarak_pulau_pemain = distance(pemain.position, mp.position)

        if pemain_diburu_pulau or jarak_pulau_pemain < 50.0:
            mp.status = "MEMBURU" if pemain_diburu_pulau else "KEJAR_PEMAIN"
            mp.look_at(Vec3(pemain.position.x, mp.position.y, pemain.position.z))
            
            kelajuan_pulau = 9.5 if getattr(mp, 'is_ketua_pulau', False) else 8.5
            mp.position += mp.forward * kelajuan_pulau * time.dt

            mp.pemasa_serang -= time.dt
            if mp.pemasa_serang <= 0:
                if getattr(mp, 'is_ketua_pulau', False):
                    if jarak_pulau_pemain < 4.0:
                        if pemain.cooldown_diserang <= 0:
                            pemain.darah -= 50
                            pemain.cooldown_diserang = 0.8
                        mp.pemasa_serang = 1.0
                    else:
                        AnakPanah(posisi=mp.position + Vec3(0, 1.8, 0), sasaran=pemain)
                        mp.pemasa_serang = 1.8
                else:
                    if jarak_pulau_pemain > 18.0:
                        AnakPanah(posisi=mp.position + Vec3(0, 1.5, 0), sasaran=pemain)
                        mp.pemasa_serang = 2.5
                    elif 5.0 <= jarak_pulau_pemain <= 18.0:
                        LembingTerbang(posisi=mp.position + Vec3(0, 1.5, 0), sasaran=pemain)
                        mp.pemasa_serang = 2.0
                    elif jarak_pulau_pemain < 3.2:
                        if pemain.cooldown_diserang <= 0:
                            pemain.darah -= 30
                            pemain.cooldown_diserang = 0.8
                        mp.pemasa_serang = 1.0

    # --- AI: MUSUH MERAH, KETUA MUSUH, RAKSASA LAUT & GLITCH ---
    for m in senarai_musuh:
        if not m or not m.enabled or getattr(m, 'is_musuh_pulau', False) or getattr(m, 'is_pintu_penjara_pulau', False): continue
        semak_dan_kemas_kini_lemas(m)

        if m.darah <= 0:
            m.enabled = False; m.collider = None 
            if hasattr(m, 'hp_text'): m.hp_text.enabled = False
            continue

        teks_titel = f"HP: {int(m.darah)}"
        if getattr(m, 'is_glitch', False): teks_titel = f"GLITCH T{m.glitch_tier}: {int(m.darah)}"
        elif getattr(m, 'is_raksasa_laut', False): teks_titel = f"穴 {m.nama.upper()} 穴\nHP: {int(m.darah)}"
        elif getattr(m, 'is_ketua', False): teks_titel = f"BOSS HP: {int(m.darah)}"

        if m.racun_timer > 0:
            m.racun_timer -= time.dt
            m.darah -= 5 * time.dt 
            m.hp_text.text = f"{teks_titel} (POISONED)"
            m.hp_text.color = color.lime

        jarak_dengan_pemain = distance(pemain.position, m.position)
        if jarak_dengan_pemain < 60.0:
            m.status = "KEJAR_PEMAIN"
            m.look_at(Vec3(pemain.position.x, m.position.y, pemain.position.z))
            
            speed_musuh = kelajuan_musuh
            if getattr(m, 'is_raksasa_laut', False): speed_musuh = m.kelajuan
            elif getattr(m, 'is_ketua', False): speed_musuh = 6
            elif getattr(m, 'is_glitch', False): speed_musuh = 7 + (m.glitch_tier * 0.5)

            m.position += m.forward * speed_musuh * time.dt
            
            if distance(pemain.position, m.position) < 4.5:
                if pemain.cooldown_diserang <= 0:
                    if getattr(m, 'is_raksasa_laut', False):
                        pemain.darah -= 65
                        pemain.cooldown_diserang = 1.0
                    elif getattr(m, 'is_glitch', False):
                        musuh_glitch_serang_pemain(m.glitch_tier)
                        if m.glitch_tier != 6:
                            pemain.darah -= m.glitch_damage
                            pemain.cooldown_diserang = 1.2
                    elif getattr(m, 'is_ketua', False):
                        pemain.darah -= 25
                        pemain.cooldown_diserang = 1.0
                    else:
                        pemain.darah -= 10
                        pemain.cooldown_diserang = 0.5

    # --- AI PEMANAH & CATAPULT ---
    for p in senarai_pemanah:
        if not p or not p.enabled: continue
        semak_dan_kemas_kini_lemas(p)
        if p.cooldown_memanah > 0:
            p.cooldown_memanah -= time.dt
            continue

        if p.is_musuh:
            if distance(p.position, pemain.position) < 40 and not pemain.dalam_penjara:
                p.look_at(pemain.position)
                AnakPanah(posisi=p.position + Vec3(0,1.5,0), sasaran=pemain)
                p.cooldown_memanah = 2.5
        else:
            musuh_terdekat = None
            jarak_musuh = 50
            for m in senarai_musuh:
                if m and m.enabled and getattr(m, 'darah', 0) > 0 and distance(p.position, m.position) < jarak_musuh:
                    musuh_terdekat = m; jarak_musuh = distance(p.position, m.position)
            if musuh_terdekat:
                p.look_at(musuh_terdekat.position)
                AnakPanah(posisi=p.position + Vec3(0,1.5,0), sasaran=musuh_terdekat)
                p.cooldown_memanah = 2.0

    for mesin in senarai_catapult:
        if not mesin or not mesin.enabled: continue
        semak_dan_kemas_kini_lemas(mesin)
        if mesin.darah <= 0:
            mesin.enabled = False; mesin.collider = None; mesin.hp_text.enabled = False
            continue

        if distance(mesin.position, pemain.position) < 80.0: 
            mesin.look_at(pemain.position)
            if mesin.cooldown_tembak > 0:
                mesin.cooldown_tembak -= time.dt
            else:
                BatuCatapult(posisi=mesin.position + Vec3(0, 3, 0), sasaran=pemain)
                mesin.cooldown_tembak = 5.0 

app.run()