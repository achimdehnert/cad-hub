#!/usr/bin/env python3
"""
Beispiel: IFC Complete Parser

Zeigt wie man alle Informationen aus einer IFC-Datei extrahiert.
"""

from pathlib import Path

from ifc_complete_parser import IfcCompleteParser, ParsedProject
import logging

logger = logging.getLogger(__name__)


def main():
    # === 1. IFC Datei parsen ===
    ifc_path = Path("model.ifc")  # Pfad zur IFC-Datei anpassen

    parser = IfcCompleteParser(ifc_path)
    project: ParsedProject = parser.parse()

    # === 2. Projekt-Informationen ===
    logger.info("=" * 60)
    logger.info(f"PROJEKT: {project.name}")
    logger.info(f"Schema: {project.schema_version.value}")
    logger.info(f"Authoring: {project.authoring_app}")
    logger.info(f"Datei: {project.file_path}")
    logger.info("=" * 60)

    # === 3. Räumliche Struktur ===
    logger.info(f"\n📍 Sites: {len(project.sites)}")
    for site in project.sites:
        logger.info(f"   - {site.name}")
        if site.latitude and site.longitude:
            logger.info(f"     Koordinaten: {site.latitude:.6f}, {site.longitude:.6f}")

    logger.info(f"\n🏢 Gebäude: {len(project.buildings)}")
    for building in project.buildings:
        logger.info(f"   - {building.name}")

    logger.info(f"\n🏗️ Geschosse: {len(project.storeys)}")
    for storey in project.storeys:
        logger.info(f"   - {storey.name} (Elevation: {storey.elevation}m)")

    # === 4. Räume mit Details ===
    logger.info(f"\n🚪 Räume: {len(project.spaces)}")
    logger.info("-" * 60)

    for space in project.spaces:
        logger.info(f"\n📦 {space.space_number or space.name} - {space.long_name or ''}")

        # Geometrie
        if space.net_floor_area:
            logger.info(f"   Fläche: {float(space.net_floor_area):.2f} m²")
        if space.net_volume:
            logger.info(f"   Volumen: {float(space.net_volume):.2f} m³")
        if space.net_height:
            logger.info(f"   Höhe: {float(space.net_height):.2f} m")

        # Brandschutz
        if space.fire_rating or space.fire_compartment:
            logger.info("   🔥 Brandschutz:")
            if space.fire_rating:
                logger.info(f"      - Feuerwiderstand: {space.fire_rating}")
            if space.fire_compartment:
                logger.info(f"      - Brandabschnitt: {space.fire_compartment}")
            if space.sprinkler_protected:
                logger.info("      - Sprinkler: Ja")

        # Ex-Zone
        if space.ex_zone:
            logger.info(f"   ⚡ Ex-Zone: {space.ex_zone}")

        # Akustik
        if space.acoustic_rating:
            logger.info(f"   🔊 Akustik: {space.acoustic_rating}")

        # Thermik
        if space.design_temperature_heating or space.design_temperature_cooling:
            logger.info("   🌡️ Thermik:")
            if space.design_temperature_heating:
                logger.info(f"      - Heizung: {float(space.design_temperature_heating):.1f}°C")
            if space.design_temperature_cooling:
                logger.info(f"      - Kühlung: {float(space.design_temperature_cooling):.1f}°C")

        # Oberflächen
        if space.finish_floor or space.finish_wall or space.finish_ceiling:
            logger.info("   🎨 Oberflächen:")
            if space.finish_floor:
                logger.info(f"      - Boden: {space.finish_floor}")
            if space.finish_wall:
                logger.info(f"      - Wand: {space.finish_wall}")
            if space.finish_ceiling:
                logger.info(f"      - Decke: {space.finish_ceiling}")

        # Alle Properties anzeigen
        if space.properties:
            logger.info(f"   📋 Properties ({len(space.properties)}):")
            for prop in space.properties[:5]:  # Max 5 anzeigen
                logger.info(f"      - {prop.pset_name}.{prop.name} = {prop.value}")
            if len(space.properties) > 5:
                logger.info(f"      ... und {len(space.properties) - 5} weitere")

    # === 5. Element-Statistiken ===
    logger.info("\n" + "=" * 60)
    logger.info("ELEMENT-STATISTIKEN")
    logger.info("=" * 60)

    for ifc_class, count in sorted(project.element_counts.items(), key=lambda x: -x[1]):
        logger.info(f"   {ifc_class}: {count}")

    # === 6. Wände mit Brandschutz ===
    logger.info("\n" + "-" * 60)
    logger.info("WÄNDE MIT BRANDSCHUTZ")
    logger.info("-" * 60)

    walls_with_fire = [
        e
        for e in project.elements
        if e.ifc_class in ("IfcWall", "IfcWallStandardCase") and e.fire_rating
    ]

    for wall in walls_with_fire[:10]:
        logger.info(f"   {wall.name or wall.global_id[:8]}")
        logger.info(f"      - Brandschutz: {wall.fire_rating}")
        logger.info(f"      - Außen: {wall.is_external}")
        logger.info(f"      - Tragend: {wall.is_load_bearing}")
        if wall.thermal_transmittance:
            logger.info(f"      - U-Wert: {float(wall.thermal_transmittance):.3f} W/(m²·K)")

    # === 7. Materialien ===
    logger.info("\n" + "-" * 60)
    logger.info(f"VERWENDETE MATERIALIEN ({len(project.all_materials)})")
    logger.info("-" * 60)

    for mat in sorted(project.all_materials):
        logger.info(f"   - {mat}")

    # === 8. Export ===
    output_path = Path("ifc_export.json")
    project.save_json(output_path)
    logger.info(f"\n✅ JSON exportiert nach: {output_path}")

    # Statistik
    logger.info("\n📊 Zusammenfassung:")
    logger.info(f"   - {len(project.spaces)} Räume")
    logger.info(f"   - {len(project.elements)} Bauelemente")
    logger.info(f"   - {len(project.element_types)} Element-Typen")
    logger.info(f"   - {len(project.all_materials)} Materialien")


def extract_fire_protection_report(project: ParsedProject) -> str:
    """Erstellt einen Brandschutz-Bericht."""
    lines = ["# Brandschutz-Bericht", ""]

    # Räume nach Brandabschnitt gruppieren
    compartments = {}
    for space in project.spaces:
        compartment = space.fire_compartment or "Nicht zugeordnet"
        if compartment not in compartments:
            compartments[compartment] = []
        compartments[compartment].append(space)

    for compartment, spaces in compartments.items():
        lines.append(f"## Brandabschnitt: {compartment}")
        lines.append("")

        total_area = sum(float(s.net_floor_area or 0) for s in spaces)
        lines.append(f"**Gesamtfläche:** {total_area:.2f} m²")
        lines.append("")

        lines.append("| Raum | Fläche | Feuerwiderstand | Sprinkler |")
        lines.append("|------|--------|-----------------|-----------|")

        for space in spaces:
            area = f"{float(space.net_floor_area):.2f} m²" if space.net_floor_area else "-"
            fire = space.fire_rating or "-"
            sprinkler = "✅" if space.sprinkler_protected else "❌"
            lines.append(f"| {space.name or space.space_number} | {area} | {fire} | {sprinkler} |")

        lines.append("")

    return "\n".join(lines)


def extract_thermal_requirements(project: ParsedProject) -> dict:
    """Extrahiert thermische Anforderungen für TGA-Planung."""
    requirements = {
        "spaces_with_heating": [],
        "spaces_with_cooling": [],
        "total_heating_load_w": 0,
        "total_cooling_load_w": 0,
    }

    for space in project.spaces:
        if space.design_heating_load:
            requirements["spaces_with_heating"].append(
                {
                    "name": space.name,
                    "area_m2": float(space.net_floor_area) if space.net_floor_area else 0,
                    "heating_load_w": float(space.design_heating_load),
                    "design_temp_c": (
                        float(space.design_temperature_heating)
                        if space.design_temperature_heating
                        else None
                    ),
                }
            )
            requirements["total_heating_load_w"] += float(space.design_heating_load)

        if space.design_cooling_load:
            requirements["spaces_with_cooling"].append(
                {
                    "name": space.name,
                    "area_m2": float(space.net_floor_area) if space.net_floor_area else 0,
                    "cooling_load_w": float(space.design_cooling_load),
                    "design_temp_c": (
                        float(space.design_temperature_cooling)
                        if space.design_temperature_cooling
                        else None
                    ),
                }
            )
            requirements["total_cooling_load_w"] += float(space.design_cooling_load)

    return requirements


if __name__ == "__main__":
    main()
