import os
import re
import json
import uuid
import textwrap
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    # L'utilisateur devra installer pdfplumber : pip install pdfplumber


BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "data" / "raw" / "pdfs"
DATA_DIR = BASE_DIR / "data2"


def read_pdf_text(pdf_path: Path) -> str:
    """
    Lit tout le texte d'un PDF et renvoie une chaîne nettoyée.
    """
    if pdfplumber is None:
        raise ImportError("pdfplumber n'est pas installé. Installe-le avec `pip install pdfplumber`.")

    if not pdf_path.exists():
        print(f"[WARN] Fichier PDF non trouvé : {pdf_path}")
        return ""

    texts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            texts.append(page_text)

    text = "\n".join(texts)
    # Nettoyage minimum
    text = text.replace("\r", "\n")
    # compacter les multi-newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def write_jsonl(out_path: Path, records):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            json.dump(rec, f, ensure_ascii=False)
            f.write("\n")
    print(f"[OK] Écrit {len(records)} lignes dans {out_path}")


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ==========================
# 1) macro_to_micro.pdf
# ==========================

def extract_macro_to_micro_rules(text: str):
    records = []

    # 1. Spécification de la forme du micro
    format_block_match = re.search(
        r"mcXX\s*[\-–].*?(?=Micro-cycle Rôle|Instructions de création)",
        text,
        flags=re.S | re.I
    )
    format_rule_text = (format_block_match.group(0).strip()
                        if format_block_match
                        else "Forme du micro-cycle définie dans macro_to_micro.pdf (Focus, Objectif, Méthode, Format, Mouvements-clés, Progression, Objectif mesurable).")

    micro_format_rec = {
        "id": "micro_format_v1",
        "source": "macro_to_micro.pdf",
        "type": "micro_format_spec",
        "applies_to": "generation",
        "role_micro": None,
        "constraints": {
            "fields_required": [
                "focus",
                "objectif",
                "methode",
                "format.series",
                "format.reps",
                "format.tempo",
                "format.intensite",
                "format.repos",
                "mouvements_cles",
                "progression",
                "objectif_mesurable",
            ],
            "tempo_required": True,
            "intensity_required": True,
            "rest_required": True
        },
        "rule_text": format_rule_text
    }
    records.append(micro_format_rec)

    # 2. Rôles des micro-cycles mc1..mc4
    # On capture le bloc qui contient le petit tableau
    roles_block_match = re.search(
        r"Micro-cycle Rôle.*?(?=À partir de cette forme|A partir de cette forme|Instructions de création)",
        text,
        flags=re.S | re.I
    )
    if roles_block_match:
        block = roles_block_match.group(0)
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        current_code = None
        current_lines = []

        def flush_role():
            if not current_code or not current_lines:
                return
            full = " ".join(current_lines)
            # Heuristique grossière : première phrase = rôle, reste = description + exemples
            role_name = full.split('"')[0].strip() if '"' in full else full
            examples = []
            for m in re.findall(r'"([^"]+)"', full):
                examples.append(m.strip())
            rec = {
                "id": make_id(current_code),
                "source": "macro_to_micro.pdf",
                "type": "micro_role",
                "applies_to": "generation",
                "role_micro": current_code,
                "constraints": {
                    "role_name": role_name,
                    "examples": examples
                },
                "rule_text": full
            }
            records.append(rec)

        for line in lines:
            m = re.match(r"(mc[1-4])\s*[\-–]?\s*$", line, flags=re.I)
            if m:
                # On change de bloc
                flush_role()
                current_code = m.group(1).lower()
                current_lines = []
            else:
                if current_code:
                    current_lines.append(line)
        flush_role()

    # 3. Instructions de création (1. à 9.)
    instr_block_match = re.search(
        r"Instructions de création\s*:(.*?)(?=Créer de la variété contrôlée|Phase 3|$)",
        text,
        flags=re.S | re.I
    )
    if instr_block_match:
        instr_block = instr_block_match.group(1).strip()
        # Découper sur les numéros "1.", "2.", etc.
        parts = re.split(r"\n(?=\d\.)", instr_block)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            mnum = re.match(r"(\d)\.\s*(.*)", part, flags=re.S)
            if not mnum:
                continue
            num = int(mnum.group(1))
            content = mnum.group(2).strip()

            # Classification simple
            if num == 1:
                rtype = "micro_format_spec"
                applies_to = "generation"
            elif num in (2, 6):
                rtype = "progression_rule"
                applies_to = "generation"
            elif num in (3, 4, 8, 9):
                rtype = "adaptation_rule"
                applies_to = "generation"
            elif num == 5:
                rtype = "progression_rule"
                applies_to = "generation"
            elif num == 7:
                rtype = "progression_rule"
                applies_to = "generation"
            else:
                rtype = "adaptation_rule"
                applies_to = "generation"

            rec = {
                "id": make_id(f"instruction_{num}"),
                "source": "macro_to_micro.pdf",
                "type": rtype,
                "applies_to": applies_to,
                "role_micro": None,
                "constraints": {
                    "instruction_number": num
                },
                "rule_text": content
            }
            records.append(rec)

    # 4. Varieté & adaptations rapides
    variety_match = re.search(
        r"Créer de la variété contrôlée\s*:(.*?)(?=Phase 3|$)",
        text,
        flags=re.S | re.I
    )
    if variety_match:
        variety_block = variety_match.group(1).strip()
        rec = {
            "id": make_id("variety"),
            "source": "macro_to_micro.pdf",
            "type": "variety_rule",
            "applies_to": "generation",
            "role_micro": None,
            "constraints": {},
            "rule_text": variety_block
        }
        records.append(rec)

    # 5. Phase 3 – Piochage intelligent + adaptation IA
    phase3_match = re.search(
        r"Phase 3\s*[\-–]\s*Piochage intelligent \+ adaptation IA(.*)$",
        text,
        flags=re.S | re.I
    )
    if phase3_match:
        phase3_block = phase3_match.group(1).strip()

        # Moteur de matching
        mmatch = re.search(r"1\.\s*Moteur de matching.*?(?=2\.)", phase3_block, flags=re.S | re.I)
        if mmatch:
            records.append({
                "id": make_id("matching"),
                "source": "macro_to_micro.pdf",
                "type": "matching_rule",
                "applies_to": "matching",
                "role_micro": None,
                "constraints": {},
                "rule_text": mmatch.group(0).strip()
            })

        # Adaptation IA
        amatch = re.search(r"2\.\s*Adaptation IA.*?(?=3\.)", phase3_block, flags=re.S | re.I)
        if amatch:
            records.append({
                "id": make_id("adaptation_ia"),
                "source": "macro_to_micro.pdf",
                "type": "adaptation_rule",
                "applies_to": "adaptation",
                "role_micro": None,
                "constraints": {},
                "rule_text": amatch.group(0).strip()
            })

        # Contrôle qualité IA
        qmatch = re.search(r"3\.\s*Contrôle qualité IA.*", phase3_block, flags=re.S | re.I)
        if qmatch:
            records.append({
                "id": make_id("quality_check"),
                "source": "macro_to_micro.pdf",
                "type": "quality_check_rule",
                "applies_to": "adaptation",
                "role_micro": None,
                "constraints": {},
                "rule_text": qmatch.group(0).strip()
            })

    return records


# ==========================
# 2) session_plan.pdf
# ==========================

def extract_session_plan(text: str):
    schema_records = []
    example_records = []

    # 1. Règles A/B/C/D
    abcd_match = re.search(
        r"🧠\s*1\.\s*Règles de déduction.*?(?=🧩\s*2\.|2\.)",
        text,
        flags=re.S
    )
    if abcd_match:
        block = abcd_match.group(0)
        for label, key in [
            ("🔹 A.", "niveau_utilisateur"),
            ("🔹 B.", "nb_seances_semaine"),
            ("🔹 C.", "macro_cycle"),
            ("🔹 D.", "micro_cycle"),
        ]:
            m = re.search(rf"{re.escape(label)}(.*?)(?=🔹 [A-D]\.|🧩 2\.|$)", block, flags=re.S)
            if m:
                content = m.group(1).strip()
                rec = {
                    "id": make_id(f"planner_rule_{key}"),
                    "source": "session_plan.pdf",
                    "type": "planner_rule",
                    "fields": {},
                    "conditions": {
                        "driver": key
                    },
                    "rule_text": content
                }
                schema_records.append(rec)

    # 2. Schéma plan_semaine (YAML-like)
    ps_match = re.search(
        r"plan_semaine:\s*\n(?:\s+.+\n)+",
        text
    )
    if ps_match:
        schema_text = ps_match.group(0).strip()
        rec = {
            "id": "planner_week_schema_v1",
            "source": "session_plan.pdf",
            "type": "planner_week_schema",
            "fields": {
                "raw_schema": schema_text
            },
            "conditions": {},
            "rule_text": schema_text
        }
        schema_records.append(rec)

    # 3. Schéma séance = 5 blocs
    session_schema_match = re.search(
        r"Chaque séance\s*=\s*5 blocs\s*:\s*(.*?)(?=\n\n|Elle pioche|$)",
        text,
        flags=re.S
    )
    if session_schema_match:
        blocks_text = session_schema_match.group(1).strip()
        blocks = []
        for part in blocks_text.split("+"):
            b = part.strip(" .:\n").strip()
            if b:
                blocks.append(b)
        rec = {
            "id": "session_schema_5_blocs_v1",
            "source": "session_plan.pdf",
            "type": "session_schema",
            "fields": {
                "blocks": blocks
            },
            "conditions": {},
            "rule_text": "Chaque séance = 5 blocs : " + ", ".join(blocks)
        }
        schema_records.append(rec)

    # 4. Exemple MC6.6
    mc_block_match = re.search(
        r"📄\s*3\.\s*Exemple concret\s*:\s*MC6\.6.*?(?=🛠 4\.|$)",
        text,
        flags=re.S
    )
    if mc_block_match:
        mc_block = mc_block_match.group(0)

        # Données disponibles
        data_match = re.search(r"Données disponibles\s*:(.*?)(?=⸻|→ Plan de semaine)", mc_block, flags=re.S)
        input_data = {}
        if data_match:
            for line in data_match.group(1).splitlines():
                line = line.strip(" •:-\n\t")
                if not line:
                    continue
                # ex: "Niveau : intermédiaire"
                m = re.match(r"([^:]+):\s*(.*)", line)
                if m:
                    key = m.group(1).strip().lower().replace(" ", "_")
                    val = m.group(2).strip()
                    input_data[key] = val

        # Plan_semaine spécifique
        ps2_match = re.search(
            r"→ Plan de semaine déduit\s*:\s*(plan_semaine:.*?)(?=\n\n|Chaque séance|$)",
            mc_block,
            flags=re.S
        )
        plan_dict = {}
        plan_text = None
        if ps2_match:
            plan_text = ps2_match.group(1).strip()
            # Parsing simple "clé: valeur"
            for line in plan_text.splitlines():
                if ":" not in line:
                    continue
                if line.strip().startswith("plan_semaine"):
                    continue
                l = line.strip()
                k, v = l.split(":", 1)
                k = k.strip()
                v = v.strip()
                plan_dict[k] = v

        # Séances exemples (Séance 1, 2, 3)
        seances_match = re.search(
            r"🛠 4\..*?(Séance 1.*)$",
            text,
            flags=re.S
        )
        seances_text = None
        if seances_match:
            seances_text = seances_match.group(1).strip()

        rec_example = {
            "id": "example_mc6_6",
            "source": "session_plan.pdf",
            "type": "planner_example",
            "meso_id": "MC6.6",
            "input": input_data,
            "output": {
                "plan_semaine": plan_dict,
                "plan_semaine_raw": plan_text,
                "seances_description": seances_text,
            },
            "rule_text": mc_block.strip()
        }
        example_records.append(rec_example)

    return schema_records, example_records


# ==========================
# 3) train_generation.pdf
# ==========================

def extract_user_profile_schema(text: str):
    """
    Parse la section "1. Prérequis (données issues du profil utilisateur)".
    """
    records = []
    preq_match = re.search(
        r"1\.\s*Prérequis.*?(?=2\.\s*Structuration temporelle)",
        text,
        flags=re.S | re.I
    )
    if not preq_match:
        return records

    block = preq_match.group(0)
    # lignes commençant par "-"
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        # ex: - niveau_sportif  :  "débutant", "intermédiaire", "avancé"
        m = re.match(r"-\s*([a-zA-Z0-9_]+)\s*:\s*(.*)", line)
        if not m:
            continue
        field_name = m.group(1).strip()
        rest = m.group(2).strip()

        domain = "text"
        allowed_values = []
        default = None

        # valeurs entre guillemets
        quoted = re.findall(r'"([^"]+)"', rest)
        if quoted:
            # check si liste
            if rest.strip().startswith("[") or "," in rest:
                domain = "enum"
            allowed_values = quoted

        # intervalle [1;10]
        if re.search(r"\[\d+;\d+\]", rest):
            domain = "int"

        rec = {
            "id": f"profil_{field_name}",
            "source": "train_generation.pdf",
            "type": "user_profile_field",
            "field_name": field_name,
            "domain": domain,
            "allowed_values": allowed_values,
            "default": default,
            "group": _guess_profile_group(field_name),
            "description": rest
        }
        records.append(rec)

    return records


def _guess_profile_group(field_name: str) -> str:
    if "objectif" in field_name:
        return "objectif"
    if "materiel" in field_name or "matériel" in field_name:
        return "materiel"
    if "patholog" in field_name or "limitation" in field_name or "troubles" in field_name or "obés" in field_name:
        return "sante"
    if "ambiance" in field_name or "style_de_communication" in field_name or "relation_au_coach" in field_name or "rythme_global" in field_name:
        return "emotionnel"
    if "jours" in field_name or "moments" in field_name or "planning" in field_name:
        return "planning"
    return "autre"


def extract_generation_spec(text: str):
    records = []

    # 2. Structuration temporelle
    struct_match = re.search(
        r"2\.\s*Structuration temporelle du programme.*?(?=📅 3\.|3\.)",
        text,
        flags=re.S | re.I
    )
    if struct_match:
        struct = struct_match.group(0)

        a_match = re.search(r"a\)\s*Durée totale cible.*?(?=b\)|$)", struct, flags=re.S | re.I)
        if a_match:
            records.append({
                "id": make_id("macrocycle"),
                "source": "train_generation.pdf",
                "type": "macrocycle_rule",
                "applies_to": "structuration",
                "inputs": [],
                "outputs": [],
                "conditions": {},
                "rule_text": a_match.group(0).strip()
            })

        b_match = re.search(r"b\)\s*Découpage en méso-cycles.*?(?=c\)|$)", struct, flags=re.S | re.I)
        if b_match:
            records.append({
                "id": make_id("mesocycle"),
                "source": "train_generation.pdf",
                "type": "mesocycle_rule",
                "applies_to": "structuration",
                "inputs": [],
                "outputs": [],
                "conditions": {},
                "rule_text": b_match.group(0).strip()
            })

        c_match = re.search(r"c\)\s*Surdécoupage en micro-cycles.*", struct, flags=re.S | re.I)
        if c_match:
            records.append({
                "id": make_id("microcycle"),
                "source": "train_generation.pdf",
                "type": "microcycle_rule",
                "applies_to": "structuration",
                "inputs": [],
                "outputs": [],
                "conditions": {},
                "rule_text": c_match.group(0).strip()
            })

    # 3. Répartition des séances
    weekly_match = re.search(
        r"📅\s*3\.\s*Répartition des séances dans la semaine.*?(?=🧩 4\.|4\.)",
        text,
        flags=re.S | re.I
    )
    if weekly_match:
        records.append({
            "id": make_id("weekly_split"),
            "source": "train_generation.pdf",
            "type": "weekly_split_rule",
            "applies_to": "weekly_planning",
            "inputs": ["nombre_de_sessions_par_semaine", "niveau_sportif", "objectif_principal"],
            "outputs": ["split", "temps_par_seance"],
            "conditions": {},
            "rule_text": weekly_match.group(0).strip()
        })

    # 4. Construction des séances
    session_match = re.search(
        r"🧩\s*4\.\s*Construction des séances.*?(?=🧠 5\.|5\.)",
        text,
        flags=re.S | re.I
    )
    if session_match:
        records.append({
            "id": make_id("session_blocks"),
            "source": "train_generation.pdf",
            "type": "session_block_rule",
            "applies_to": "session_construction",
            "inputs": ["niveau_sportif"],
            "outputs": ["structure_seance"],
            "conditions": {},
            "rule_text": session_match.group(0).strip()
        })

    # 5. Choix des exercices
    ex_match = re.search(
        r"🧠\s*5\.\s*Choix des exercices.*?(?=🛠 6\.|6\.)",
        text,
        flags=re.S | re.I
    )
    if ex_match:
        records.append({
            "id": make_id("exercise_choice"),
            "source": "train_generation.pdf",
            "type": "exercise_choice_rule",
            "applies_to": "exercise_selection",
            "inputs": ["objectif_principal", "zone_musculaire"],
            "outputs": ["type_exercice"],
            "conditions": {},
            "rule_text": ex_match.group(0).strip()
        })

    # 6. Adaptation au matériel
    eq_match = re.search(
        r"🛠\s*6\.\s*Adaptation au matériel.*?(?=📄 7\.|7\.)",
        text,
        flags=re.S | re.I
    )
    if eq_match:
        records.append({
            "id": make_id("equipment"),
            "source": "train_generation.pdf",
            "type": "equipment_rule",
            "applies_to": "exercise_selection",
            "inputs": ["materiel_disponible"],
            "outputs": ["type_exercice"],
            "conditions": {},
            "rule_text": eq_match.group(0).strip()
        })

    # 7. Format de sortie MVP
    out_match = re.search(
        r"📄\s*7\.\s*Format de sortie MVP.*?(?=🧪 8\.|8\.)",
        text,
        flags=re.S | re.I
    )
    if out_match:
        records.append({
            "id": make_id("output_format"),
            "source": "train_generation.pdf",
            "type": "output_format_rule",
            "applies_to": "output_format",
            "inputs": [],
            "outputs": ["texte_seance"],
            "conditions": {},
            "rule_text": out_match.group(0).strip()
        })

    # 8. Profils de test
    test_match = re.search(
        r"🧪\s*8\.\s*Profils d'exemples.*?(?=🔵|GROUPE 1|$)",
        text,
        flags=re.S | re.I
    )
    if test_match:
        records.append({
            "id": make_id("test_profiles"),
            "source": "train_generation.pdf",
            "type": "test_profile_rule",
            "applies_to": "testing",
            "inputs": [],
            "outputs": [],
            "conditions": {},
            "rule_text": test_match.group(0).strip()
        })

    return records


def extract_objective_priority(text: str):
    """
    Parse les blocs GROUPE 1/2/3 avec sous-domaines (🏋, ⚡, 🧘, 🥦, 🔄).
    """
    records = []

    group_blocks = re.split(r"(🔵|🟠|🔴)\s*", text)
    # group_blocks = [before, symbol1, block1, symbol2, block2, ...]
    symbol_to_group = {"🔵": 1, "🟠": 2, "🔴": 3}

    for i in range(1, len(group_blocks), 2):
        symbol = group_blocks[i]
        block = group_blocks[i + 1]
        group_num = symbol_to_group.get(symbol)
        if not group_num:
            continue

        # Extraire sous-domaines
        current_subdomain = None
        buffer_lines = []
        def flush_subdomain():
            if not current_subdomain or not buffer_lines:
                return
            text_block = "\n".join(buffer_lines).strip()
            objectives = []
            for line in buffer_lines:
                line = line.strip()
                if line.startswith("●"):
                    obj = line.lstrip("●").strip()
                    if obj:
                        objectives.append(obj)
            if not objectives:
                return
            rec = {
                "id": make_id(f"objective_group_{group_num}_{current_subdomain}"),
                "source": "train_generation.pdf",
                "type": "objective_priority",
                "group": group_num,
                "subdomain": current_subdomain,
                "objectives": objectives,
                "priority": "haute" if group_num == 1 else ("moyenne" if group_num == 2 else "basse"),
                "rule_text": text_block
            }
            records.append(rec)

        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # détecter les emojis de sous-domaine
            if stripped.startswith("🏋"):
                flush_subdomain()
                current_subdomain = "physique"
                buffer_lines = [stripped]
            elif stripped.startswith("⚡"):
                flush_subdomain()
                current_subdomain = "performance"
                buffer_lines = [stripped]
            elif stripped.startswith("🧘"):
                flush_subdomain()
                current_subdomain = "bien_etre"
                buffer_lines = [stripped]
            elif stripped.startswith("🥦"):
                flush_subdomain()
                current_subdomain = "metabolisme"
                buffer_lines = [stripped]
            elif stripped.startswith("🔄"):
                flush_subdomain()
                current_subdomain = "hybride"
                buffer_lines = [stripped]
            else:
                if current_subdomain:
                    buffer_lines.append(stripped)

        flush_subdomain()

    return records


# ==========================
# MAIN
# ==========================

def main():
    print(f"[INFO] Dossier de travail : {DATA_DIR}")
    print(f"[INFO] Dossier PDF : {PDF_DIR}")

    # 1) macro_to_micro
    macro_path = PDF_DIR / "macro_to_micro.pdf"
    if macro_path.exists():
        print(f"\n[INFO] Traitement de {macro_path.name}")
        text = read_pdf_text(macro_path)
        macro_records = extract_macro_to_micro_rules(text)
        write_jsonl(DATA_DIR / "macro_to_micro_rules.jsonl", macro_records)
    else:
        print(f"[WARN] macro_to_micro.pdf non trouvé dans {PDF_DIR}")

    # 2) session_plan
    session_path = PDF_DIR / "session_plan.pdf"
    if session_path.exists():
        print(f"\n[INFO] Traitement de {session_path.name}")
        text = read_pdf_text(session_path)
        schema_records, example_records = extract_session_plan(text)
        write_jsonl(DATA_DIR / "planner_schema.jsonl", schema_records)
        write_jsonl(DATA_DIR / "planner_examples.jsonl", example_records)
    else:
        print(f"[WARN] session_plan.pdf non trouvé dans {PDF_DIR}")

    # 3) train_generation
    tg_path = PDF_DIR / "train_generation.pdf"
    if tg_path.exists():
        print(f"\n[INFO] Traitement de {tg_path.name}")
        text = read_pdf_text(tg_path)

        profile_records = extract_user_profile_schema(text)
        gen_spec_records = extract_generation_spec(text)
        obj_priority_records = extract_objective_priority(text)

        write_jsonl(DATA_DIR / "user_profile_schema.jsonl", profile_records)
        write_jsonl(DATA_DIR / "generation_spec.jsonl", gen_spec_records)
        write_jsonl(DATA_DIR / "objective_priority.jsonl", obj_priority_records)
    else:
        print(f"[WARN] train_generation.pdf non trouvé dans {PDF_DIR}")

    print("\n[DONE] Extraction terminée.")


if __name__ == "__main__":
    main()

