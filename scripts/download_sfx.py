#!/usr/bin/env python3
"""Download Star Trek sound effects from trekcore.com using actual page hrefs."""
import sys
import os
from pathlib import Path
import urllib.request
import urllib.error

LIBRARY_DIR = Path(__file__).resolve().parent.parent / "sfx_library"
BASE_URL = "https://www.trekcore.com/audio"

SFX_FILES = [
    # Background ambience
    "background/voy_bridge.mp3",
    "background/voy_engineering.mp3",
    "background/voy_astrometrics.mp3",
    "background/voy_core_1.mp3",
    "background/voy_core_2.mp3",
    "background/voy_core_3.mp3",
    "background/voy_core_4.mp3",
    "background/voy_relativity_bridge.mp3",
    "background/tng_bridge_1.mp3",
    "background/tng_bridge_2.mp3",
    "background/tng_bridge_3.mp3",
    "background/tng_sickbay.mp3",
    "background/tng_sickbay_2.mp3",
    "background/tng_engine_1.mp3",
    "background/tng_engine_2.mp3",
    "background/tng_engine_3.mp3",
    "background/tng_engineering_hum.mp3",
    "background/tng_hum_clean.mp3",
    "background/tng_lab.mp3",
    "background/tng_cargobay.mp3",
    "background/tng_jeffreystube.mp3",
    "background/tng_data_room.mp3",
    "background/tng_brig.mp3",
    "background/ds9_infirmary.mp3",
    # Borg sounds
    "aliensounds/borg_adapt.mp3",
    "aliensounds/borg_adapt2.mp3",
    "aliensounds/borg_adapt3.mp3",
    "aliensounds/borg_adapt4.mp3",
    "aliensounds/borg_beam_clean.mp3",
    "aliensounds/borg_cut_clean.mp3",
    "aliensounds/borg_cut_2.mp3",
    "aliensounds/borg_cut_3.mp3",
    "aliensounds/borg_engine_hum.mp3",
    "aliensounds/borg_phaser_clean.mp3",
    "aliensounds/borg_flyby.mp3",
    "aliensounds/borg_sound_1.mp3",
    "aliensounds/borg_sound_2.mp3",
    "aliensounds/borg_sound_3.mp3",
    "aliensounds/borg_sound_4.mp3",
    "aliensounds/borg_stepping.mp3",
    "aliensounds/borg_struck_phaser.mp3",
    "aliensounds/borg_tractor_beam.mp3",
    "aliensounds/borg_transporter.mp3",
    "aliensounds/borg_transporter_2.mp3",
    "aliensounds/borg_computer_beep.mp3",
    "aliensounds/borg_alcove_regen_cycle.mp3",
    "aliensounds/borg_alcove_regen_cycle_abort.mp3",
    # Computer sounds (TNG era, numbered)
    "computer/alarm01.mp3", "computer/alarm02.mp3", "computer/alarm03.mp3",
    "computer/alert01.mp3", "computer/alert02.mp3", "computer/alert03.mp3",
    "computer/alert04.mp3", "computer/alert05.mp3", "computer/alert06.mp3",
    "computer/computerbeep_1.mp3", "computer/computerbeep_2.mp3",
    "computer/computerbeep_3.mp3", "computer/computerbeep_4.mp3",
    "computer/computerbeep_5.mp3", "computer/computerbeep_6.mp3",
    "computer/computerbeep_7.mp3", "computer/computerbeep_8.mp3",
    "computer/computerbeep_9.mp3", "computer/computerbeep_10.mp3",
    "computer/consolewarning.mp3",
    "computer/damagealarm.mp3",
    "computer/critical.mp3",
    "computer/hailalert_1.mp3", "computer/hailalert_2.mp3",
    "computer/hailingfrequencies_open1.mp3",
    "computer/hailingfrequencies_open2.mp3",
    "computer/hailingfrequencies_open3.mp3",
    "computer/hailingfrequencies_open4.mp3",
    "computer/keyok1.mp3", "computer/keyok2.mp3",
    "computer/keyok3.mp3", "computer/keyok4.mp3",
    "computer/keyok5.mp3", "computer/keyok6.mp3",
    "computer/energize.mp3", "computer/engage.mp3",
    "computer/processing.mp3", "computer/computer_error.mp3",
    "computer/transporter_beep.mp3",
    "computer/voy_hail.mp3",
    # Door sounds
    "doors/voy_door_chime_1.mp3",
    "doors/voy_door_chime_2.mp3",
    "doors/tng_door_open.mp3",
    "doors/tng_door_close.mp3",
    "doors/tng_cargobay.mp3",
    "doors/tng_doors_1.mp3",
    "doors/tng_doors_2.mp3",
    # Medical
    "medical/hypospray_1.mp3",
    "medical/hypospray_2.mp3",
    "medical/hypospray_3.mp3",
    "medical/laser_scalpel.mp3",
    "medical/medical_scanner_bay.mp3",
    # Red Alert
    "redalert/voy_red_alert.mp3",
    "redalert/voy_red_alert_2.mp3",
    "redalert/voy_intruder_alert.mp3",
    "redalert/voy_blue_alert.mp3",
    "redalert/alert_klaxon_1.mp3",
    "redalert/alert_klaxon_2.mp3",
    # Transporter
    "transporter/voy_transporter_1.mp3",
    "transporter/voy_transporter_2.mp3",
    "transporter/voy_unstable_transporter.mp3",
    "transporter/tng_transporter_1.mp3",
    "transporter/tng_transporter_2.mp3",
    # Replicator
    "replicator/voy_sickbay_replicator.mp3",
    "replicator/tng_replicator.mp3",
    # Turbolift
    "turbolift/voy_turbolift.mp3",
    "turbolift/tng_turbolift.mp3",
    "turbolift/tng_turbolift_1.mp3",
    "turbolift/tng_turbolift_2.mp3",
    # Weapons (TNG/VOY)
    "weapons/tng_phaser_1.mp3",
    "weapons/tng_phaser_2.mp3",
    "weapons/tng_phaser_3.mp3",
    "weapons/tng_torpedo_1.mp3",
    "weapons/tng_torpedo_2.mp3",
    "weapons/tng_torpedo_3.mp3",
    "weapons/tng_phaser_rifle.mp3",
    # Warp
    "warp/tng_warp_1.mp3",
    "warp/tng_warp_2.mp3",
    "warp/tng_warp_3.mp3",
    "warp/tng_warp_4.mp3",
    "warp/tng_warp_5.mp3",
    "warp/tng_warp_6.mp3",
    # Explosions
    "explosions/console_explode_1.mp3",
    "explosions/console_explode_2.mp3",
    "explosions/console_explode_3.mp3",
    "explosions/large_explosion_1.mp3",
    "explosions/large_explosion_2.mp3",
    "explosions/small_explosion_1.mp3",
    "explosions/small_explosion_2.mp3",
    # Holodeck
    "holodeck/holodeck_end_program.mp3",
    "holodeck/hologram_on.mp3",
    "holodeck/hologram_off_1.mp3",
    "holodeck/hologram_off_2.mp3",
    "holodeck/hologrid_online.mp3",
    "holodeck/hologrid_failing.mp3",
    # Tricorder
    "tricorder/tng_tricorder_1.mp3",
    "tricorder/tng_tricorder_2.mp3",
    "tricorder/tng_tricorder_3.mp3",
    "tricorder/tng_tricorder_4.mp3",
    "tricorder/tng_tricorder_5.mp3",
    # Communicator
    "communicator/tng_chirp_clean.mp3",
    "communicator/tng_chirp2_clean.mp3",
    "communicator/tng_chirp3_clean.mp3",
    # Beep sequences
    "computer/sequences/ambient_bridge_1.mp3",
    "computer/sequences/ambient_bridge_2.mp3",
    "computer/sequences/engineering_clean.mp3",
    "computer/sequences/helm_beep_sequence.mp3",
    "computer/sequences/ops_beep_sequence.mp3",
    "computer/sequences/tactical_beep_sequence.mp3",
    "computer/sequences/sensor.mp3",
    "computer/sequences/computer_sounds.mp3",
    "computer/sequences/computerbeepsequence1.mp3",
    "computer/sequences/astrometrics_controls.mp3",
    # Voice announcements
    "computer/voice/autodestructsequencearmed_ep.mp3",
    "computer/voice/autoinitationemh.mp3",
    "computer/voice/evacuatebridge_ep.mp3",
    "computer/voice/incomingtransmission_clean.mp3",
    "computer/voice/intruderalertdeck8_ep.mp3",
    "computer/voice/priorityonemessagefromstarfleet_ep.mp3",
    "computer/voice/selfdestructsequenceinitiatedwarpcorebreach_ep.mp3",
    "computer/voice/unabletocomply.mp3",
    "computer/voice/diagnosticcomplete_ep.mp3",
    "computer/voice/warningprimaryshieldsfailing_ep.mp3",
    "computer/voice/warningwarpcorecollapse_ep.mp3",
    "computer/voice/securityauthorisationaccepted_clean.mp3",
    # PADD
    "computer/padd/padd_1.mp3",
    "computer/padd/padd_2.mp3",
    "computer/padd/padd_3.mp3",
]


def download_file(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HolodeckStudio/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        if len(data) < 1024:
            dest.unlink(missing_ok=True)
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        dest.unlink(missing_ok=True)
        return False


def main():
    downloaded = 0
    failed = 0
    skipped = 0

    for rel_path in SFX_FILES:
        url = f"{BASE_URL}/{rel_path}"
        dest = LIBRARY_DIR / rel_path
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        if download_file(url, dest):
            downloaded += 1
        else:
            failed += 1

    total = len(SFX_FILES)
    print(f"Total: {total}, Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    main()
