#!/usr/bin/env python3
"""
scripts/verify_report.py
------------------------
Script automatizado de auditoría y verificación pre-entrega para el informe
técnico de SmartStay (Startup Sísifo) en formato Markdown.
Curso: 1ASI0722 Agile Project Management (Ciclo 2026-20)
Profesor: Rouillon Sixto César Elías

Comprobaciones implementadas:
  1. Comprobación de Fotografías de Integrantes (Sección 3.1.2)
  2. Alerta de Student Outcome (ABET 2 - TB2)
  3. Control de Erratas Residuales (ej. RapiFast, CanchaYa)
  4. Control de Coherencia Arquitectónica en Project Charter (Monolito por Capas)

Código de salida:
  0: Todas las comprobaciones pasaron satisfactoriamente y el informe está listo.
  1: Se detectaron errores bloqueantes o advertencias críticas que impiden la entrega.
"""

import sys
import os
import re
import argparse
from typing import List, Dict, Tuple, Optional

# Definición de códigos ANSI para formato en consola
RED_BOLD = "\033[1;31m"
GREEN_BOLD = "\033[1;32m"
YELLOW_BOLD = "\033[1;33m"
CYAN_BOLD = "\033[1;36m"
WHITE_BOLD = "\033[1;37m"
RESET = "\033[0m"

VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PROHIBITED_WORDS = [
    "RapiFast",
    "rapifast",
    "CanchaYa",
    "canchaya",
    "TravelMate",
    "travelmate",
    "Health Advisor",
    "HealthAdvisor",
    "health advisor"
]

CONTRADICTORY_ARCHITECTURE_TERMS = [
    "microservicio",
    "microservicios",
    "microservice",
    "microservices"
]

EXPECTED_MEMBERS = [
    {
        "id": "italo",
        "display_name": "Italo Sebastian Verona Flores",
        "search_pattern": r"Verona|Italo"
    },
    {
        "id": "eddo",
        "display_name": "Su Caletti Eddo",
        "search_pattern": r"Su Caletti|Eddo"
    },
    {
        "id": "oskar",
        "display_name": "Oskar Rodrigo Sosa Soto",
        "search_pattern": r"Sosa|Oskar"
    },
    {
        "id": "ever",
        "display_name": "Ever Giusephi Carlos Lavado",
        "search_pattern": r"Carlos|Lavado|Ever"
    },
    {
        "id": "augusto",
        "display_name": "Augusto Sebastian Montes Maza",
        "search_pattern": r"Montes|Augusto"
    }
]


def resolve_report_path(explicit_path: Optional[str] = None) -> str:
    """Localiza el archivo Markdown del informe en el repositorio."""
    if explicit_path:
        if os.path.isfile(explicit_path):
            return os.path.abspath(explicit_path)
        raise FileNotFoundError(f"Archivo especificado no encontrado: {explicit_path}")

    # Candidatos por defecto según el directorio de ejecución
    candidates = [
        "Report/README.md",
        "README.md",
        "../Report/README.md",
        "docs/README.md",
        "Report/docs/README.md"
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)

    # Búsqueda recursiva de README.md
    for root, _, files in os.walk("."):
        if ".git" in root:
            continue
        if "README.md" in files:
            return os.path.abspath(os.path.join(root, "README.md"))

    raise FileNotFoundError("No se encontró ningún archivo README.md en el repositorio.")


def check_member_photos(markdown_content: str, doc_dir: str) -> Tuple[bool, List[str]]:
    """
    1. Comprobación de Fotografías (Sección 3.1.2):
       Verifica que cada uno de los 5 integrantes tenga una imagen asociada válida,
       que exista físicamente en disco, su tamaño sea > 0 KB y extensión permitida.
    """
    errors: List[str] = []
    
    # Extraer la sección 3.1.2
    sec_match = re.search(
        r"### 3\.1\.2\.\s*Perfiles de Integrantes del Equipo(.*?)(?=## 3\.2|\Z)",
        markdown_content,
        re.DOTALL | re.IGNORECASE
    )
    if not sec_match:
        errors.append("No se encontró la sección '3.1.2. Perfiles de Integrantes del Equipo' en el informe.")
        return False, errors

    sec_content = sec_match.group(1)

    for member in EXPECTED_MEMBERS:
        pat = member["search_pattern"]
        name = member["display_name"]

        # Buscar el bloque del integrante
        m_match = re.search(
            rf"####\s*Integrante[^:]*:[^\n]*({pat})[^\n]*(.*?)(?=####\s*Integrante|\Z)",
            sec_content,
            re.DOTALL | re.IGNORECASE
        )
        if not m_match:
            errors.append(f"No se encontró la sección de perfil para el integrante: {name}")
            continue

        block = m_match.group(0)

        # Buscar etiqueta de imagen (markdown o html img)
        img_match = re.search(
            r"""<img[^>]+src=["']([^"']+)["']|!\[.*?\]\((.*?)\)""",
            block,
            re.IGNORECASE
        )
        if not img_match:
            errors.append(f"El integrante '{name}' no tiene asociada una imagen válida (![...] o <img>).")
            continue

        img_rel_path = img_match.group(1) or img_match.group(2)
        # Normalizar y resolver ruta física relativa
        img_full_path = os.path.normpath(os.path.join(doc_dir, img_rel_path))

        # Validar existencia física
        if not os.path.isfile(img_full_path):
            errors.append(
                f"La imagen de '{name}' ({img_rel_path}) no existe físicamente en: {img_full_path}"
            )
            continue

        # Validar tamaño > 0 KB
        file_size = os.path.getsize(img_full_path)
        if file_size <= 0:
            errors.append(
                f"La imagen de '{name}' ({img_rel_path}) tiene un tamaño de 0 KB (archivo vacío o corrupto)."
            )
            continue

        # Validar extensión
        _, ext = os.path.splitext(img_rel_path)
        ext = ext.lower()
        if ext not in VALID_IMAGE_EXTENSIONS:
            errors.append(
                f"La imagen de '{name}' ({img_rel_path}) tiene una extensión inválida '{ext}'. "
                f"Permitidas: {', '.join(sorted(VALID_IMAGE_EXTENSIONS))}"
            )
            continue

    return len(errors) == 0, errors


def check_student_outcome_tb2(markdown_content: str) -> Tuple[bool, List[str]]:
    """
    2. Alerta de Student Outcome (ABET 2 - TB2):
       Verifica que existan registros explícitos para TB2 tanto en las acciones
       individuales de los 5 integrantes como en las conclusiones grupales.
    """
    warnings: List[str] = []

    so_match = re.search(r"# Student Outcome(.*?)(?=\n# |\Z)", markdown_content, re.DOTALL | re.IGNORECASE)
    if not so_match:
        warnings.append("No se encontró la sección '# Student Outcome' en el informe.")
        return False, warnings

    so_text = so_match.group(1)

    # Identificar filas de la tabla de criterios
    rows = [line for line in so_text.split("\n") if line.strip().startswith("|") and ("**Criterio" in line or "Criterio" in line)]
    if not rows:
        warnings.append("No se encontró la tabla de criterios en la sección Student Outcome.")
        return False, warnings

    # Verificar registro de TB2 por cada uno de los 5 integrantes
    missing_members_tb2 = []
    for member in EXPECTED_MEMBERS:
        pat = member["search_pattern"]
        name = member["display_name"]
        member_has_tb2 = False

        for r in rows:
            cols = [c.strip() for c in r.split("|")[1:-1]]
            if len(cols) >= 2:
                actions_col = cols[1]
                # Buscar bloque del integrante en la columna de acciones
                m_sec = re.search(rf"\*\*[^*]*({pat})[^*]*\*\*(.*?)(?=\*\*[A-Z]|\Z)", actions_col, re.DOTALL | re.IGNORECASE)
                if m_sec:
                    sec_text = m_sec.group(2)
                    if "TB2" in sec_text:
                        # Verificar que tenga contenido explicativo real tras 'TB2'
                        after_tb2 = sec_text.split("TB2")[-1].strip()
                        # Limpiar etiquetas HTML como <br>
                        clean_after = re.sub(r"<[^>]+>", "", after_tb2).strip()
                        if len(clean_after) > 15:
                            member_has_tb2 = True
                            break

        if not member_has_tb2:
            missing_members_tb2.append(name)

    # Verificar conclusiones grupales para TB2
    conclusiones_has_tb2 = False
    for r in rows:
        cols = [c.strip() for c in r.split("|")[1:-1]]
        if len(cols) >= 3:
            concl_col = cols[2]
            if "TB2" in concl_col:
                after_tb2 = concl_col.split("TB2")[-1].strip()
                clean_concl = re.sub(r"<[^>]+>", "", after_tb2).strip()
                if len(clean_concl) > 15:
                    conclusiones_has_tb2 = True
                    break

    if missing_members_tb2:
        warnings.append(
            f"Faltan registros explícitos de acciones realizadas para TB2 en {len(missing_members_tb2)} integrante(s): "
            + ", ".join(missing_members_tb2)
        )

    if not conclusiones_has_tb2:
        warnings.append("No se encontraron Conclusiones Grupales registradas para la entrega TB2.")

    # Si solo hay datos de TB1
    if "TB1" in so_text and (missing_members_tb2 or not conclusiones_has_tb2):
        warnings.append(
            "La tabla de Student Outcome contiene actualmente información correspondiente a TB1; "
            "los registros de TB2 están ausentes o incompletos."
        )

    return len(warnings) == 0, warnings


def check_prohibited_words(markdown_content: str) -> Tuple[bool, List[str]]:
    """
    3. Control de Erratas Residuales:
       Detecta nombres obsoletos o heredados de otros proyectos (ej. RapiFast, CanchaYa).
    """
    errors: List[str] = []
    lines = markdown_content.split("\n")

    for line_idx, line in enumerate(lines, 1):
        for word in PROHIBITED_WORDS:
            # Búsqueda insensible a mayúsculas/minúsculas pero reportando el término
            matches = list(re.finditer(rf"\b{re.escape(word)}\b", line, re.IGNORECASE))
            for m in matches:
                matched_text = m.group(0)
                snippet = line.strip()
                if len(snippet) > 80:
                    start_char = max(0, m.start() - 25)
                    end_char = min(len(line), m.end() + 25)
                    snippet = "..." + line[start_char:end_char].strip() + "..."
                errors.append(
                    f"Línea {line_idx}: Palabra prohibida detectada '{matched_text}' -> \"{snippet}\""
                )

    return len(errors) == 0, errors


def check_architectural_coherence(markdown_content: str) -> Tuple[bool, List[str]]:
    """
    4. Control de Coherencia Arquitectónica:
       Verifica que en la sección del Project Charter (4.1) no existan menciones
       a microservicios u otros términos contradictorios con la Arquitectura Monolítica por Capas.
    """
    errors: List[str] = []

    # Extraer el Project Charter (sección 4.1 hasta la siguiente sección de primer nivel o bibliografía)
    charter_match = re.search(
        r"## 4\.1\.\s*Agile Project Integration Management: Project Charter(.*?)(?=\n# |\Z)",
        markdown_content,
        re.DOTALL | re.IGNORECASE
    )
    if not charter_match:
        errors.append("No se encontró la sección '4.1. Project Charter' en el informe.")
        return False, errors

    charter_text = charter_match.group(0)
    charter_start_char = charter_match.start()

    # Calcular índice de línea para reportar números de línea exactos
    charter_line_offset = markdown_content[:charter_start_char].count("\n") + 1
    charter_lines = charter_text.split("\n")

    for idx, line in enumerate(charter_lines):
        line_num = charter_line_offset + idx
        for term in CONTRADICTORY_ARCHITECTURE_TERMS:
            matches = list(re.finditer(rf"\b{re.escape(term)}\b", line, re.IGNORECASE))
            for m in matches:
                matched_term = m.group(0)
                snippet = line.strip()
                if len(snippet) > 80:
                    start_char = max(0, m.start() - 25)
                    end_char = min(len(line), m.end() + 25)
                    snippet = "..." + line[start_char:end_char].strip() + "..."
                errors.append(
                    f"Línea {line_num}: Término arquitectónico contradictorio '{matched_term}' "
                    f"en Project Charter -> \"{snippet}\""
                )

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(
        description="Auditoría y verificación pre-entrega de SmartStay (Startup Sísifo) - Curso 1ASI0722."
    )
    parser.add_argument(
        "--file", "-f",
        dest="file_path",
        help="Ruta al archivo Markdown a auditar (ej. Report/README.md). Auto-detectado si se omite."
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help="Si se activa, las advertencias de TB2 no forzarán exit code 1 (solo errores fatales fallarán)."
    )

    args = parser.parse_args()

    print(f"\n{CYAN_BOLD}{'='*75}{RESET}")
    print(f"{CYAN_BOLD} SMARTSTAY - AUDITORÍA Y VERIFICACIÓN PRE-ENTREGA (SEMANA 6 - 2026-20){RESET}")
    print(f"{CYAN_BOLD} Startup Sísifo | Curso: Agile Project Management (1ASI0722){RESET}")
    print(f"{CYAN_BOLD}{'='*75}{RESET}\n")

    try:
        report_file = resolve_report_path(args.file_path)
    except FileNotFoundError as e:
        print(f"{RED_BOLD}[ERROR FATAL] {e}{RESET}")
        sys.exit(1)

    print(f"📄 Archivo analizado: {WHITE_BOLD}{os.path.relpath(report_file)}{RESET}")
    doc_dir = os.path.dirname(report_file)

    with open(report_file, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    total_errors = 0
    total_warnings = 0

    # -------------------------------------------------------------
    # Comprobación 1: Fotografías de Integrantes
    # -------------------------------------------------------------
    print(f"\n{WHITE_BOLD}1. Verificación de Fotografías de Integrantes (Sección 3.1.2):{RESET}")
    photos_ok, photo_errors = check_member_photos(markdown_content, doc_dir)
    if photos_ok:
        print(f"   {GREEN_BOLD}✔ [PASS]{RESET} Todos los 5 integrantes cuentan con fotografía válida, existente (>0 KB) y extensión permitida.")
        for member in EXPECTED_MEMBERS:
            print(f"      • {member['display_name']}: {GREEN_BOLD}Conforme{RESET}")
    else:
        print(f"   {RED_BOLD}✖ [FALLO]{RESET} Discrepancias encontradas en las fotografías de integrantes:")
        for err in photo_errors:
            print(f"      - {RED_BOLD}{err}{RESET}")
        total_errors += len(photo_errors)

    # -------------------------------------------------------------
    # Comprobación 2: Alerta de Student Outcome (ABET 2 - TB2)
    # -------------------------------------------------------------
    print(f"\n{WHITE_BOLD}2. Alerta de Student Outcome (ABET 2 - TB2):{RESET}")
    tb2_ok, tb2_warnings = check_student_outcome_tb2(markdown_content)
    if tb2_ok:
        print(f"   {GREEN_BOLD}✔ [PASS]{RESET} Tabla de Student Outcome completada con registros de TB2 para los 5 integrantes y conclusiones grupales.")
    else:
        # EMISIÓN DE ADVERTENCIA CRÍTICA EN ROJO (Requerimiento explícito)
        print(f"   {RED_BOLD}⚠️  [ADVERTENCIA CRÍTICA EN ROJO] EL INFORME NO ESTÁ LISTO PARA LA ENTREGA DE TB2:{RESET}")
        for w in tb2_warnings:
            print(f"      {RED_BOLD}• {w}{RESET}")
        total_warnings += len(tb2_warnings)

    # -------------------------------------------------------------
    # Comprobación 3: Control de Erratas Residuales
    # -------------------------------------------------------------
    print(f"\n{WHITE_BOLD}3. Control de Erratas Residuales:{RESET}")
    erratas_ok, errata_errors = check_prohibited_words(markdown_content)
    if erratas_ok:
        print(f"   {GREEN_BOLD}✔ [PASS]{RESET} No se detectaron nombres heredados ni palabras prohibidas ({', '.join(PROHIBITED_WORDS[:4])}, ...).")
    else:
        print(f"   {RED_BOLD}✖ [FALLO]{RESET} Se encontraron palabras prohibidas en el informe:")
        for err in errata_errors:
            print(f"      - {RED_BOLD}{err}{RESET}")
        total_errors += len(errata_errors)

    # -------------------------------------------------------------
    # Comprobación 4: Control de Coherencia Arquitectónica
    # -------------------------------------------------------------
    print(f"\n{WHITE_BOLD}4. Control de Coherencia Arquitectónica (Project Charter):{RESET}")
    arch_ok, arch_errors = check_architectural_coherence(markdown_content)
    if arch_ok:
        print(f"   {GREEN_BOLD}✔ [PASS]{RESET} Arquitectura unificada a Monolito por Capas (DDD + PostgreSQL). Cero menciones a microservicios en el Project Charter.")
    else:
        print(f"   {RED_BOLD}✖ [FALLO]{RESET} Se detectaron contradicciones técnicas en el Project Charter:")
        for err in arch_errors:
            print(f"      - {RED_BOLD}{err}{RESET}")
        total_errors += len(arch_errors)

    # -------------------------------------------------------------
    # Resumen y Código de Salida
    # -------------------------------------------------------------
    print(f"\n{CYAN_BOLD}{'='*75}{RESET}")
    print(f"{CYAN_BOLD} RESUMEN DE LA AUDITORÍA{RESET}")
    print(f"{CYAN_BOLD}{'='*75}{RESET}")
    print(f"  • Errores Bloqueantes: {RED_BOLD if total_errors > 0 else GREEN_BOLD}{total_errors}{RESET}")
    print(f"  • Advertencias Críticas: {RED_BOLD if total_warnings > 0 else GREEN_BOLD}{total_warnings}{RESET}")

    if total_errors == 0 and total_warnings == 0:
        print(f"\n{GREEN_BOLD}✔ RESULTADO: APROBADO (Exit Code 0). El informe cumple con todos los estándares y está listo para la entrega.{RESET}\n")
        sys.exit(0)
    elif total_errors == 0 and total_warnings > 0:
        if args.allow_warnings:
            print(f"\n{YELLOW_BOLD}⚠ RESULTADO: APROBADO CON ADVERTENCIAS (--allow-warnings activado, Exit Code 0).{RESET}\n")
            sys.exit(0)
        else:
            print(
                f"\n{RED_BOLD}✖ RESULTADO: FALLO PRE-ENTREGA (Exit Code 1). "
                f"El informe presenta advertencias críticas (Student Outcome TB2 incompleto) que impiden la entrega formal.{RESET}"
            )
            print(f"{YELLOW_BOLD}  Nota: Para ignorar advertencias durante desarrollo preliminar, use --allow-warnings.{RESET}\n")
            sys.exit(1)
    else:
        print(f"\n{RED_BOLD}✖ RESULTADO: FALLO (Exit Code 1). Se detectaron {total_errors} error(es) bloqueante(s) que deben corregirse.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
