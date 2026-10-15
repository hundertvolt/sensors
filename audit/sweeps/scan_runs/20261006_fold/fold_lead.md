# Lead's own fold parts (phase 1 seams)
SF-B8 (SYSTEM half) | M.SRC_CORE.017 (2) | src/system_service.py get_dict_cfg | U11 per entry | TEST_UNIT: unreadable SYSTEM store -> {"SYSTEM": {"error":"unavailable"}}; SPEC C.6 marker sentence covers SYSTEM too
SF-B1, SF-B12 (SGP40 halves) | M.SRC_SENS.062 (1) | src/asy_sgp40_driver.py construction | U15 | TEST_UNIT: SGP40 chunk owner distinct from its logger's owner; refused backup chunk -> one _WRN_SGP_NO_BACKUP "Backup storage unavailable" per boot; TSC seed-distinct check includes the SGP40 owner name
SF-M3-04 seam | M.SRC_SENS.075 text uses _verify_config() (renamed by .077 (1))
SF-M3-09 (SGP40 half) | none in source: the register's fix is one SPEC sentence (SPEC carrier)
