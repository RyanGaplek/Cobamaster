import requests
import time
import sys
import random
import os
import json
import threading

# ================== KONFIGURASI MASTER ==================
BASE_URL = "https://cdn.moltyroyale.com/api"
TURN_DELAY = 60  

# 🔥 DAFTAR KARYAWAN TUYUL (MASUKKAN API KEY DI SINI) 🔥
# WAJIB BEDA-BEDA API KEY BIAR GAK NYANGKUT!
DAFTAR_TUYUL = [
    {"nama": "🔴 dotpeaxel", "api_key": "mr_live_U2yiRuK46ZC2rB9xcz4ORKDv3u4n_j2G"},
    {"nama": "🔵 peaxel", "api_key": "mr_live_NWIeDJOAgPt7rmNVFcuVZu9QFcydmCYI"},
    {"nama": "🟢 peaxel2", "api_key": "mr_live_Ax2zvzirGueozKHGpdOA6m0hgnbOcVpx"},
    {"nama": "🟡 peaxel3", "api_key": "mr_live_3WYDHqvJgpEVpilKGGZ_pww_u7rcY_GF"},
    {"nama": "🟣 peaxel4", "api_key": "mr_live_1cEZm2NYLdMK4Rx7YTvFwe6xuj7qaCvD"}
]

# ================== FUNGSI GLOBAL (LOGIKA MURNI) ==================
def get_waktu():
    return time.strftime('%H:%M:%S')

def cari_barang_di_tanah(state, region):
    items = state.get("visibleItems", [])
    if not items: items = region.get("items", [])
    if not items: items = state.get("items", [])
    if not items: items = state.get("droppedItems", [])
    return items

def ekstrak_info_item(item_data):
    if isinstance(item_data, (str, int)):
        return str(item_data), "Barang Misterius"
    elif isinstance(item_data, dict):
        item_id = item_data.get("id") or item_data.get("_id") or item_data.get("itemId") or item_data.get("uid")
        item_name = item_data.get("name") or item_data.get("typeId") or "Loot"
        
        if "item" in item_data and isinstance(item_data["item"], dict):
            data_asli = item_data["item"]
            if not item_name or item_name == "Loot":
                item_name = data_asli.get("name") or data_asli.get("typeId") or "Barang"
            if not item_id: item_id = data_asli.get("id")
                
        if not item_id:
            for key, val in item_data.items():
                if isinstance(val, str) and len(val) > 10 and key not in ["name", "type", "description", "regionId"]:
                    item_id = val; break
        return str(item_id), str(item_name)
    return None, None

def is_valid_weapon(item_name, item_data):
    name_lower = str(item_name).lower()
    blacklist = ["fist", "none", "bandage", "medkit", "ration", "potion", "moltz", "coin", "emergency", "megaphone", "radio"]
    for word in blacklist:
        if word in name_lower: return False
    if isinstance(item_data, dict):
        i_data = item_data.get("item", item_data)
        if isinstance(i_data, dict):
            item_type = str(i_data.get("type", "")).lower()
            if item_type != "" and "weapon" not in item_type: return False
    if any(w in name_lower for w in ["sniper", "rifle", "katana", "pistol", "gun", "sword", "bow", "knife", "dagger"]): return True
    return False

def get_weapon_score(weapon_name):
    name_lower = str(weapon_name).lower()
    if "fist" in name_lower or "none" in name_lower: return 0
    if "sniper" in name_lower or "rifle" in name_lower: return 60
    if "katana" in name_lower: return 50
    if "pistol" in name_lower or "gun" in name_lower: return 40
    if "sword" in name_lower: return 30
    if "bow" in name_lower: return 20
    if "knife" in name_lower or "dagger" in name_lower: return 10
    return 5 

def sort_loot_priority(item_data):
    _, name = ekstrak_info_item(item_data)
    nl = str(name).lower()
    if "bandage" in nl or "medkit" in nl or "ration" in nl or "potion" in nl or "emergency" in nl: return 100 
    if "moltz" in nl or "coin" in nl: return 90 
    if "sniper" in nl or "katana" in nl or "rifle" in nl: return 80 
    if "pistol" in nl or "sword" in nl or "gun" in nl: return 75
    return 10

def cari_pintu_strategis(pintu_aman, region_dict, hp_sekarat):
    if not pintu_aman: return None
    ruins = []; forests = []; others = []
    for r_id in pintu_aman:
        region_data = region_dict.get(str(r_id).lower(), {})
        terrain = str(region_data.get('terrain', '')).lower()
        if 'ruins' in terrain: ruins.append(r_id)
        elif 'forest' in terrain: forests.append(r_id)
        else: others.append(r_id)
        
    if hp_sekarat and forests: return random.choice(forests)
    if not hp_sekarat and ruins: return random.choice(ruins)
    return random.choice(pintu_aman)

# ================== CLASS MESIN BOT (MULTI-THREADING) ==================
class TuyulWorker(threading.Thread):
    def __init__(self, nama, api_key):
        super().__init__()
        self.bot_name = nama
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json", "X-API-Key": self.api_key}
        
        # Bikin nama file memori bersih dari emoji biar sistem gak error
        nama_bersih = "".join(c for c in nama if c.isalnum())
        self.session_file = f"session_{nama_bersih}.json"

    def smart_print(self, bot_memory, text):
        if bot_memory.get("last_log_msg") != text:
            print(f"[{get_waktu()}] {text}")
            bot_memory["last_log_msg"] = text

    def load_session(self):
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    return data.get("game_id"), data.get("agent_id")
            except Exception: pass
        return None, None

    def save_session(self, game_id, agent_id):
        try:
            with open(self.session_file, "w") as f:
                json.dump({"game_id": game_id, "agent_id": agent_id}, f)
        except Exception: pass

    def clear_session(self):
        if os.path.exists(self.session_file):
            try:
                os.remove(self.session_file)
            except Exception: pass

    def get_waiting_game(self):
        MAX_PERCOBAAN = 5
        print(f"🔍 [{get_waktu()}] [{self.bot_name}] Mencari room GRATIS...")
        url = f"{BASE_URL}/games?status=waiting"
        
        for attempt in range(1, MAX_PERCOBAAN + 1):
            try:
                response = requests.get(url, timeout=15)
                res = response.json()
                if res.get("success") and res.get("data"):
                    for game in res["data"]:
                        if game.get("status", "").lower() == "waiting" and game.get("entryType", "").lower() != "paid":
                            print(f"✅ [{get_waktu()}] [{self.bot_name}] Menemukan Room: {game.get('name')}")
                            return game["id"]
            except Exception: pass
            if attempt < MAX_PERCOBAAN: time.sleep(10)
                
        print(f"⏳ [{get_waktu()}] [{self.bot_name}] Tidak ada room gratis. Nunggu giliran...")
        return None

    def register_agent(self, game_id):
        print(f"🧾 [{get_waktu()}] [{self.bot_name}] Mendaftar ke room...")
        try:
            res = requests.post(f"{BASE_URL}/games/{game_id}/agents/register", headers=self.headers, json={"name": self.bot_name}).json()
            
            if not res.get("success"):
                pesan_error = str(res.get("error", {}).get("message", "Error misterius"))
                print(f"⚠️ [{get_waktu()}] [{self.bot_name}] Ditolak masuk: {pesan_error}")
                
                # 🔥 SISTEM ANTI-KLONING (TIDAK MEMBELAH DIRI) 🔥
                if "one agent per apikey" in pesan_error.lower() or "already" in pesan_error.lower():
                    print(f"⏳ [{get_waktu()}] [{self.bot_name}] NYANGKUT! Nunggu 60 detik biar mati di game sebelah...")
                    time.sleep(60) 
                return None 
                
            agent_id = res["data"]["id"]
            print(f"✅ [{get_waktu()}] [{self.bot_name}] Terdaftar! (ID: {agent_id})")
            return agent_id
        except Exception as e:
            return None

    def start_game(self, game_id):
        requests.post(f"{BASE_URL}/games/{game_id}/start", headers=self.headers)

    def get_state(self, game_id, agent_id):
        try:
            res_raw = requests.get(f"{BASE_URL}/games/{game_id}/agents/{agent_id}/state", headers=self.headers, timeout=10)
            if res_raw.status_code in [400, 403, 404]: return "MATI"
            res = res_raw.json()
            if not res.get("success"): return "MATI"
            return res.get("data")
        except requests.exceptions.Timeout: return None
        except Exception: return None

    def send_action(self, game_id, agent_id, action_payload):
        try:
            return requests.post(f"{BASE_URL}/games/{game_id}/agents/{agent_id}/action", headers=self.headers, json={"action": action_payload}, timeout=10).json()
        except Exception: return None

    def decide_action(self, state, bot_memory):
        self_data = state.get("self", {})
        try: my_hp_val = int(self_data.get("hp", 100))
        except: my_hp_val = 100
            
        my_id = self_data.get("id")
        region = state.get("currentRegion", {})
        current_region_id = region.get("id")
        visible_regions = state.get("visibleRegions", [])
        adjacent_regions = state.get("connectedRegions") or region.get("connections") or state.get("visibleRegions") or []
        adjacent_ids = [str(r.get("id") if isinstance(r, dict) else r).lower() for r in adjacent_regions]
        
        region_dict = {}
        for r in visible_regions + state.get("connectedRegions", []) + [region]:
            if isinstance(r, dict):
                r_id = str(r.get("id", "")).lower()
                if r_id: region_dict[r_id] = r

        if "dz_memory" not in bot_memory: bot_memory["dz_memory"] = set()
        if "pdz_memory" not in bot_memory: bot_memory["pdz_memory"] = set()
        if "sampah_memory" not in bot_memory: bot_memory["sampah_memory"] = set()

        if current_region_id != bot_memory.get("last_region_id"):
            bot_memory["last_region_id"] = current_region_id

        game_data = state.get("game", {})
        raw_pdz = state.get("pendingDeathzones", []) + state.get("pendingDeathZones", []) + game_data.get("pendingDeathzones", [])
        raw_dz = state.get("deathzones", []) + state.get("deathZones", []) + game_data.get("deathzones", [])

        for pdz in raw_pdz:
            if isinstance(pdz, dict): bot_memory["pdz_memory"].add(str(pdz.get("id", "")).lower())
            else: bot_memory["pdz_memory"].add(str(pdz).lower())

        for dz in raw_dz:
            if isinstance(dz, dict): bot_memory["dz_memory"].add(str(dz.get("id", "")).lower())
            else: bot_memory["dz_memory"].add(str(dz).lower())

        current_r_id = str(current_region_id).lower()
        current_r_name = str(region.get("name", "")).lower()
        
        is_death_zone_now = region.get("isDeathZone", False)
        if current_r_id in bot_memory["dz_memory"] or current_r_name in bot_memory["dz_memory"]: is_death_zone_now = True

        is_pending_dz_now = False
        if current_r_id in bot_memory["pdz_memory"] or current_r_name in bot_memory["pdz_memory"]: is_pending_dz_now = True
            
        interactables = region.get("interactables", [])
        id_medical = None; id_supply = None
        for fac in interactables:
            if not fac.get("isUsed"):  
                fac_name = str(fac.get("name", "")).lower()
                fac_id = fac.get("id")
                if "medical" in fac_name: id_medical = fac_id
                elif "supply" in fac_name: id_supply = fac_id
                
        inventory = self_data.get("inventory", [])
        id_potion = None; id_bandage = None
        tangan_kosong = True; equipped_w_score = 0; equipped_w_name = "Tangan Kosong"; weapon_range = 0
        best_inv_w_id = None; best_inv_w_name = None; best_inv_w_score = -1
        
        equipped_item = self_data.get("equippedWeapon") or self_data.get("weapon")
        if equipped_item:
            _, equipped_w_name_raw = ekstrak_info_item(equipped_item)
            nm_low = equipped_w_name_raw.lower()
            if "fist" in nm_low or "none" in nm_low:
                tangan_kosong = True; equipped_w_score = 0
            else:
                tangan_kosong = False; equipped_w_name = equipped_w_name_raw; equipped_w_score = get_weapon_score(equipped_w_name_raw)
                if any(w in nm_low for w in ["bow", "pistol", "sniper", "rifle", "gun"]): weapon_range = 1

        for item in inventory:
            is_equipped = item.get("isEquipped", False) if isinstance(item, dict) else False
            item_id, item_name = ekstrak_info_item(item)
            name_lower = str(item_name).lower()
            
            if is_equipped:
                if "fist" in name_lower or "none" in name_lower: tangan_kosong = True; equipped_w_score = 0
                else:
                    tangan_kosong = False; equipped_w_name = item_name; equipped_w_score = get_weapon_score(item_name)
                    if any(w in name_lower for w in ["bow", "pistol", "sniper", "rifle", "gun"]): weapon_range = 1
                continue

            if "bandage" in name_lower or "medkit" in name_lower or "emergency" in name_lower:
                if not id_bandage: id_bandage = item_id 
            elif "ration" in name_lower or "potion" in name_lower:
                if not id_potion: id_potion = item_id 
                
            if is_valid_weapon(item_name, item):
                score = get_weapon_score(item_name)
                if score > best_inv_w_score:
                    best_inv_w_score = score; best_inv_w_id = item_id; best_inv_w_name = item_name

        musuh_player = []; musuh_monster = []
        semua_orang = state.get("visibleAgents", []) + state.get("visibleNpcs", []) + state.get("visibleMonsters", []) + state.get("monsters", []) + region.get("npcs", []) + region.get("monsters", [])
        
        for a in semua_orang:
            if a.get("isAlive", True) and a.get("id") != my_id:
                m_reg_id = str(a.get("regionId")).lower()
                jarak_ke_musuh = 0 if m_reg_id == current_r_id else (1 if m_reg_id in adjacent_ids else 99)
                
                if jarak_ke_musuh <= weapon_range:
                    if "peaxel" in str(a.get("name", "")).lower(): continue 
                    is_monster = False
                    if "type" in a and a["type"] in ["monster", "npc"]: is_monster = True
                    if any(m in str(a.get("name", "")).lower() for m in ["wolf", "bear", "bandit"]): is_monster = True
                    
                    a['jarak'] = jarak_ke_musuh
                    if is_monster: musuh_monster.append(a)
                    else: musuh_player.append(a)

        musuh_player.sort(key=lambda x: x.get("hp", 100))
        musuh_monster.sort(key=lambda x: x.get("hp", 100))
        
        musuh_player_terlemah = musuh_player[0] if musuh_player else None
        musuh_monster_terlemah = musuh_monster[0] if musuh_monster else None
        jumlah_pengeroyok = len([m for m in musuh_player if m.get("jarak") == 0])

        barang_di_area = cari_barang_di_tanah(state, region)
        barang_di_area.sort(key=sort_loot_priority, reverse=True)

        def aksi_move(pesan_kustom="🚪 Pindah ruangan..."):
            if not adjacent_regions: return None 
            pintu_aman = []; pintu_blind = []; pintu_pending = []
            
            for r in adjacent_regions:
                raw_id = r.get("id") if isinstance(r, dict) else r
                if not raw_id: continue
                r_id = str(raw_id).lower()
                r_obj = region_dict.get(r_id, {})
                
                is_dz = False; is_pdz = False
                if r_id in bot_memory["dz_memory"]: is_dz = True
                if r_id in bot_memory["pdz_memory"]: is_pdz = True
                if r_obj.get("isDeathZone") or r_obj.get("isDeathzone"): is_dz = True
                if r_obj.get("isPendingDeathZone") or r_obj.get("isPendingDeathzone"): is_pdz = True
                
                if not is_dz: 
                    if is_pdz: pintu_pending.append(raw_id)
                    elif r_obj: pintu_aman.append(raw_id)
                    else: pintu_blind.append(raw_id)
                    
            target_id = None
            if len(pintu_aman) > 0:
                ruangan_sebelumnya = bot_memory["visited_path"][-1] if len(bot_memory["visited_path"]) > 0 else None
                pilihan_bebas = [r for r in pintu_aman if r != ruangan_sebelumnya]
                
                if len(pilihan_bebas) > 0: target_id = cari_pintu_strategis(pilihan_bebas, region_dict, my_hp_val < 60)
                else: target_id = cari_pintu_strategis(pintu_aman, region_dict, my_hp_val < 60)
                self.smart_print(bot_memory, f"[{self.bot_name}] 🏃 {pesan_kustom}")
                
            elif len(pintu_blind) > 0:
                target_id = random.choice(pintu_blind)
                self.smart_print(bot_memory, f"[{self.bot_name}] 🏃 {pesan_kustom}")
            elif len(pintu_pending) > 0:
                target_id = random.choice(pintu_pending)
                self.smart_print(bot_memory, f"[{self.bot_name}] 🏃 {pesan_kustom}")

            if target_id:
                if current_region_id in bot_memory["visited_path"]: bot_memory["visited_path"].remove(current_region_id)
                bot_memory["visited_path"].append(current_region_id)
                if len(bot_memory["visited_path"]) > 15: bot_memory["visited_path"].pop(0)
                return {"type": "move", "regionId": target_id}
            return None 
            
        def aksi_serang(target_id, target_type): return {"type": "attack", "targetId": target_id, "targetType": target_type}
        def aksi_pungut(item_data): 
            item_id, _ = ekstrak_info_item(item_data)
            return {"type": "pickup", "itemId": item_id} 
        def aksi_pakai_item(item_id): return {"type": "use_item", "itemId": item_id} 
        def aksi_equip(item_id): return {"type": "equip", "itemId": item_id}
        def aksi_interact(fasilitas_id): return {"type": "interact", "interactableId": fasilitas_id}
        def aksi_buang(item_id, pesan_kustom="Membuang barang..."): 
            self.smart_print(bot_memory, f"[{self.bot_name}] 🗑️ {pesan_kustom}")
            return {"type": "drop", "itemId": item_id}

        # ================== INSTING KILAT ==================
        if best_inv_w_id:
            if tangan_kosong:
                self.smart_print(bot_memory, f"[{self.bot_name}] 🗡️ Tangan kosong! Pasang [{best_inv_w_name}] (INSTANT)!")
                return aksi_equip(best_inv_w_id)
            elif best_inv_w_score > equipped_w_score:
                self.smart_print(bot_memory, f"[{self.bot_name}] ✨ UPGRADE SENJATA! Pakai [{best_inv_w_name}] (INSTANT)!")
                return aksi_equip(best_inv_w_id)

        # 🔥 AUTO-CLEAN (SAPU JAGAT) DENGAN INGATAN ANTI-SPAM 🔥
        skor_maksimal_kita = max(equipped_w_score, best_inv_w_score)
        for item in inventory:
            is_eq = item.get("isEquipped", False) if isinstance(item, dict) else False
            if not is_eq:
                i_id, i_name = ekstrak_info_item(item)
                nm_low = i_name.lower()
                
                if i_id in bot_memory["sampah_memory"]: continue 

                if "megaphone" in nm_low or "radio" in nm_low:
                    bot_memory["sampah_memory"].add(i_id) 
                    return aksi_buang(i_id, f"AUTO-CLEAN: Buang {i_name} (Menuhin tas doang)!")
                    
                if is_valid_weapon(i_name, item):
                    skor_tas = get_weapon_score(i_name)
                    if skor_tas < skor_maksimal_kita:
                        bot_memory["sampah_memory"].add(i_id) 
                        return aksi_buang(i_id, f"AUTO-CLEAN: Buang {i_name} usang. Udah megang yang dewa!")

        # ================== PUNGUT BARANG ==================
        if len(barang_di_area) > 0:
            item_terbaik = barang_di_area[0]
            _, nama_barang = ekstrak_info_item(item_terbaik)
            tas_penuh = True if len(inventory) >= 10 else False
            is_koin = True if "moltz" in nama_barang.lower() or "coin" in nama_barang.lower() else False
            
            if not tas_penuh or is_koin:
                self.smart_print(bot_memory, f"[{self.bot_name}] 🎒 Sikat Secepat Kilat: {nama_barang}!")
                return aksi_pungut(item_terbaik)

        # ================== CEK COOLDOWN ==================
        sisa_cd = bot_memory.get("group1_cd_end", 0) - time.time()
        if sisa_cd > 0: return {"type": "WAITING_CD"}

        # ================== AKSI BERAT & SURVIVAL ==================
        is_trapped_in_dz = False
        if is_death_zone_now or is_pending_dz_now:
            aksi_lari = aksi_move("KABUR DARI ZONA MERAH!")
            if aksi_lari: return aksi_lari
            else: is_trapped_in_dz = True

        batas_heal = 95 if is_trapped_in_dz else 80
        if my_hp_val < batas_heal:
            if id_medical:
                self.smart_print(bot_memory, f"[{self.bot_name}] 🏥 Pakai Medical Facility Gratis!")
                return aksi_interact(id_medical)
            elif id_bandage:
                self.smart_print(bot_memory, f"[{self.bot_name}] 🚑 Pakai Obat (Bandage/Emergency)!")
                return aksi_pakai_item(id_bandage)
            elif id_potion:
                self.smart_print(bot_memory, f"[{self.bot_name}] 🚑 Pakai Potion/Rations!")
                return aksi_pakai_item(id_potion)

        if jumlah_pengeroyok >= 2 and my_hp_val < 70:
            aksi = aksi_move("Dikeroyok Player! Mundur taktis!")
            if aksi: return aksi

        # 🔥 LOGIKA TERPOJOK (GLADIATOR MODE) 🔥
        if musuh_player_terlemah:
            target = musuh_player_terlemah
            hp_musuh = target.get("hp", 100); nama_musuh = target.get("name", "Player"); jarak_musuh = target.get("jarak", 0)
            
            if tangan_kosong:
                aksi = aksi_move("Tangan kosong! Kabur nyari senjata...")
                if aksi: return aksi
                self.smart_print(bot_memory, f"[{self.bot_name}] 👊 JALAN BUNTU! Terpaksa tinju {nama_musuh}!")
                return aksi_serang(target.get("id"), "agent")

            if hp_musuh <= 40:
                self.smart_print(bot_memory, f"[{self.bot_name}] 😈 MANGSA EMPUK! Bantai {nama_musuh} (HP:{hp_musuh})!")
                return aksi_serang(target.get("id"), "agent")

            if jarak_musuh > 0 and weapon_range > 0:
                self.smart_print(bot_memory, f"[{self.bot_name}] 🎯 SNIPER MODE! Cicil {nama_musuh} dari jauh!")
                return aksi_serang(target.get("id"), "agent")
                
            aksi = aksi_move(f"Musuh sehat (HP:{hp_musuh}). Hindari konflik, cari aman!")
            if aksi: return aksi

            self.smart_print(bot_memory, f"[{self.bot_name}] ⚔️ ZONA MENTOK! Duel maut lawan {nama_musuh}!")
            return aksi_serang(target.get("id"), "agent")

        if musuh_monster_terlemah:
            target = musuh_monster_terlemah
            nama_musuh = target.get("name", "Monster")
            
            if not tangan_kosong and my_hp_val > 60:
                self.smart_print(bot_memory, f"[{self.bot_name}] 👹 Bantai Monster untuk Koin!")
                return aksi_serang(target.get("id"), "monster")
            else:
                aksi = aksi_move(f"Mundur dari {nama_musuh}...")
                if aksi: return aksi
                return aksi_serang(target.get("id"), "monster")

        if id_supply:
            self.smart_print(bot_memory, f"[{self.bot_name}] 📦 Area aman! Buka Supply Cache!")
            return aksi_interact(id_supply)

        aksi_akhir = aksi_move("Patroli cari Loot/Obat")
        if aksi_akhir: return aksi_akhir
            
        return {"type": "explore"}

    def print_live_status(self, state, game_id):
        self_data = state.get("self", {})
        hp = self_data.get('hp', '?')
        tas = len(self_data.get('inventory', []))
        
        senjata_info = "Tangan Kosong 👊"
        equipped_item = self_data.get("equippedWeapon") or self_data.get("weapon")
        if equipped_item:
            _, nm = ekstrak_info_item(equipped_item)
            if "fist" not in nm.lower() and "none" not in nm.lower(): senjata_info = f"{nm} 🗡️"
                
        print(f"\n[🎮 GAME {game_id[-5:]}] [{self.bot_name}] | HP:{hp} | Tas:{tas}/10 | Senj: {senjata_info}")

    def cetak_laporan_kemenangan(self, state):
        print(f"\n🏆 [{self.bot_name}] WINNER WINNER CHICKEN DINNER! 🏆\n")

    def cetak_laporan_forensik(self, current_state):
        print(f"\n💀 [{self.bot_name}] MATI GUGUR DI MEDAN PERANG! 💀\n")

    # ================== LOOPING UTAMA PER TUYUL ==================
    def run(self):
        while True: # LOOP ABADI ANTI-MATI
            game_id, agent_id = self.load_session()
            resume_berhasil = False
            
            if game_id and agent_id:
                print(f"🔄 [{get_waktu()}] [{self.bot_name}] Coba RECONNECT ke game sebelumnya...")
                state = self.get_state(game_id, agent_id)
                if state and state != "MATI":
                    is_alive = state.get("self", {}).get("isAlive", True)
                    status_game = state.get("gameStatus", "").lower()
                    if status_game not in ["finished", "cancelled"] and is_alive:
                        print(f"✅ [{get_waktu()}] [{self.bot_name}] RECONNECT BERHASIL!")
                        resume_berhasil = True
                    else:
                        self.clear_session()
                else:
                    self.clear_session()
                    
            if not resume_berhasil:
                agent_id = None; game_id = None
                while not agent_id:
                    game_id = self.get_waiting_game()
                    if not game_id:
                        time.sleep(10)
                        continue
                    agent_id = self.register_agent(game_id)
                    if not agent_id: time.sleep(5)
                        
                self.save_session(game_id, agent_id)
                self.start_game(game_id)
                print(f"⏳ [{get_waktu()}] [{self.bot_name}] Menunggu game dimulai...")
                
                while True:
                    state = self.get_state(game_id, agent_id)
                    if state == "MATI":
                        self.clear_session()
                        break
                    if state and state.get("gameStatus", "").lower() not in ["waiting", "created", "pending", ""]:
                        print(f"🔥 [{get_waktu()}] [{self.bot_name}] GAME DIMULAI! MELEPAS BOT 🔥\n")
                        break
                    time.sleep(1) 

            bot_memory = {
                "visited_path": [], "dz_memory": set(), "pdz_memory": set(), 
                "taunted_agents": set(), "sampah_memory": set(),
                "last_region_id": None, "last_state": None, 
                "group1_cd_end": 0, "last_print_time": 0, "last_log_msg": ""
            }

            while True:
                try:
                    state = self.get_state(game_id, agent_id)
                    
                    if state == "MATI" or not state:
                        self.clear_session()
                        break
                        
                    bot_memory["last_state"] = state
                    
                    if not state.get("self", {}).get("isAlive"):
                        self.cetak_laporan_forensik(state)
                        self.clear_session()
                        break
                        
                    if state.get("gameStatus") == "finished":
                        if state.get("self", {}).get("isAlive"): self.cetak_laporan_kemenangan(state)
                        self.clear_session()
                        break
                    
                    if time.time() - bot_memory["last_print_time"] >= 30:
                        self.print_live_status(state, game_id)
                        bot_memory["last_print_time"] = time.time()
                        bot_memory["last_log_msg"] = "" 

                    action_payload = self.decide_action(state, bot_memory)
                    
                    if action_payload:
                        if action_payload.get("type") == "WAITING_CD":
                            time.sleep(1.5)
                            continue
                            
                        act_type = action_payload.get("type", "")
                        res = self.send_action(game_id, agent_id, action_payload)
                        
                        if res and res.get("success"):
                            if act_type in ["pickup", "equip", "talk", "whisper", "drop"]: time.sleep(0.2) 
                            else: 
                                bot_memory["group1_cd_end"] = time.time() + TURN_DELAY
                                time.sleep(1) 
                        else: time.sleep(1) 
                    else: time.sleep(1)
                except Exception:
                    time.sleep(1)

# ================== EKSEKUSI MASTER ==================
if __name__ == "__main__":
    print("==================================================")
    print("🚀 PABRIK TUYUL MULTI-THREADING DIAKTIFKAN! 🚀")
    print("==================================================\n")
    
    threads = []
    
    # Menjalankan setiap bot di jalurnya masing-masing
    for tuyul in DAFTAR_TUYUL:
        if tuyul["api_key"].startswith("ISI_"):
            print(f"⚠️ Melewati {tuyul['nama']} karena API KEY belum diisi.")
            continue
            
        pekerja = TuyulWorker(tuyul["nama"], tuyul["api_key"])
        pekerja.daemon = True # Biar bot ikut mati kalau file master dimatikan
        pekerja.start()
        threads.append(pekerja)
        
        # Kasih jeda 2 detik tiap ngelepas 1 bot biar server gamenya gak kaget
        time.sleep(2) 
        
    if not threads:
        print("❌ Tidak ada bot yang aktif! Cek API KEY di konfigurasi.")
        sys.exit(1)
        
    print("\n👀 Semua bot berhasil dilepas ke alam gaib. Master memantau...\n")
    
    # Tahan program utama biar gak langsung ketutup
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Dihentikan oleh Bos! Menarik semua pasukan...")
        sys.exit(0)