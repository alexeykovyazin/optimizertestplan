# JOB-light: детальный разбор ключевых запросов (прогон 27.10.2026)

Сравнение: бейслин 8e23f5f87eea (HQbird 5.0.5 @3055, кеш 2048 стр./256M temp)
vs прогон 27.10 (v5.0-impr-opt f54cbf8fac @3056, 19 многоколоночных статистик,
кеш 50000 стр./2000M temp). Протокол обоих: warmup+1 замер.
Планы: детальные (prepare-фаза). Чексуммы COUNT(*) стабильны.

## job_light_049

```sql
SELECT COUNT(*) FROM title t,movie_info mi,movie_companies mc,cast_info ci WHERE t.id=mi.movie_id AND t.id=mc.movie_id AND t.id=ci.movie_id AND ci.role_id=2 AND mi.info_type_id=16
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | таймаут >300 с | 89.9 с |
| отношение к бейслину | — | — |
| строк/чексумма | — | 1 / sha1:0b9afddbea205d3… (FINISHED-WAS-TIMEOUT) |
| fetches/reads | — | — |

**План бейслина (плоский):** `PLAN JOIN (MI INDEX (INFO_TYPE_ID_MOVIE_INFO), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES), CI INDEX (MOVIE_ID_CAST_INFO))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Nested Loop Join (inner)
            -> Filter
                -> Table "MOVIE_INFO" as "MI" Access By ID
                    -> Bitmap
                        -> Index "INFO_TYPE_ID_MOVIE_INFO" Range Scan (full match)
            -> Filter
                -> Table "TITLE" as "T" Access By ID
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
            -> Filter
                -> Table "CAST_INFO" as "CI" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_CAST_INFO" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN HASH (HASH (HASH (MC NATURAL, T NATURAL), MI INDEX (INFO_TYPE_ID_MOVIE_INFO)), CI INDEX (ROLE_ID_CAST_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Filter (rows=10467262.08)
            -> Batch Hash Join (inner) (batches: 2) (rows=10467262.08)
                -> Record Buffer (record length: 75) (rows=3663668.82)
                    -> Hash Join (inner) (rows=3663668.82)
                        -> Hash Join (inner) (rows=2609129.00)
                            -> Table "MOVIE_COMPANIES" as "MC" Full Scan (rows=2609129.00)
                            -> Record Buffer (record length: 25) (rows=2528312.00)
                                -> Table "TITLE" as "T" Full Scan (rows=2528312.00)
                        -> Record Buffer (record length: 33) (rows=3550187.76)
                            -> Filter (rows=3550187.76)
                                -> Table "MOVIE_INFO" as "MI" Access By ID (rows=3550187.76)
                                    -> Bitmap
                                        -> Index "INFO_TYPE_ID_MOVIE_INFO" Range Scan (full match)
                -> Record Buffer (record length: 33) (rows=7223497.98)
                    -> Filter (rows=7223497.98)
                        -> Table "CAST_INFO" as "CI" Access By ID (rows=7223497.98)
                            -> Bitmap
                                -> Index "ROLE_ID_CAST_INFO" Range Scan (full match)
```

---

## job_light_050

```sql
SELECT COUNT(*) FROM title t,movie_info mi,movie_companies mc,cast_info ci WHERE t.id=mi.movie_id AND t.id=mc.movie_id AND t.id=ci.movie_id AND ci.role_id=2 AND mi.info_type_id=16 AND t.production_year>2000
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | таймаут >300 с | 56.32 с |
| отношение к бейслину | — | — |
| строк/чексумма | — | 1 / sha1:e8d329a2a979398… (FINISHED-WAS-TIMEOUT) |
| fetches/reads | — | — |

**План бейслина (плоский):** `PLAN JOIN (MI INDEX (INFO_TYPE_ID_MOVIE_INFO), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES), CI INDEX (MOVIE_ID_CAST_INFO))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Nested Loop Join (inner)
            -> Filter
                -> Table "MOVIE_INFO" as "MI" Access By ID
                    -> Bitmap
                        -> Index "INFO_TYPE_ID_MOVIE_INFO" Range Scan (full match)
            -> Filter
                -> Table "TITLE" as "T" Access By ID
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
            -> Filter
                -> Table "CAST_INFO" as "CI" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_CAST_INFO" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN HASH (HASH (JOIN (T NATURAL, MC INDEX (MOVIE_ID_MOVIE_COMPANIES)), MI INDEX (INFO_TYPE_ID_MOVIE_INFO)), CI INDEX (ROLE_ID_CAST_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Filter (rows=6170277.31)
            -> Batch Hash Join (inner) (batches: 2) (rows=6170277.31)
                -> Record Buffer (record length: 75) (rows=2159671.98)
                    -> Hash Join (inner) (rows=2159671.98)
                        -> Nested Loop Join (inner) (rows=1538038.25)
                            -> Filter (rows=1384676.93)
                                -> Table "TITLE" as "T" Full Scan (rows=2528312.00)
                            -> Filter (rows=1.11)
                                -> Table "MOVIE_COMPANIES" as "MC" Access By ID (rows=1.11)
                                    -> Bitmap
                                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
                        -> Record Buffer (record length: 33) (rows=3550187.76)
                            -> Filter (rows=3550187.76)
                                -> Table "MOVIE_INFO" as "MI" Access By ID (rows=3550187.76)
                                    -> Bitmap
                                        -> Index "INFO_TYPE_ID_MOVIE_INFO" Range Scan (full match)
                -> Record Buffer (record length: 33) (rows=7223497.98)
                    -> Filter (rows=7223497.98)
                        -> Table "CAST_INFO" as "CI" Access By ID (rows=7223497.98)
                            -> Bitmap
                                -> Index "ROLE_ID_CAST_INFO" Range Scan (full match)
```

---

## job_light_041

```sql
SELECT COUNT(*) FROM title t,movie_info mi,movie_companies mc,movie_keyword mk WHERE t.id=mi.movie_id AND t.id=mk.movie_id AND t.id=mc.movie_id AND mi.info_type_id=16 AND t.production_year>2000
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | 137.9 с | 239.0 с |
| отношение к бейслину | — | 1.73 |
| строк/чексумма | 1 / sha1:89a285a0a98e3a7… | 1 / sha1:89a285a0a98e3a7… (match) |
| fetches/reads | 561 959 749 | — |

**План бейслина (плоский):** `PLAN JOIN (MI INDEX (INFO_TYPE_ID_MOVIE_INFO), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES), MK INDEX (MOVIE_ID_MOVIE_KEYWORD))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Nested Loop Join (inner)
            -> Filter
                -> Table "MOVIE_INFO" as "MI" Access By ID
                    -> Bitmap
                        -> Index "INFO_TYPE_ID_MOVIE_INFO" Range Scan (full match)
            -> Filter
                -> Table "TITLE" as "T" Access By ID
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
            -> Filter
                -> Table "MOVIE_KEYWORD" as "MK" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_KEYWORD" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN HASH (HASH (HASH (MK NATURAL, T NATURAL), MC NATURAL), MI INDEX (INFO_TYPE_ID_MOVIE_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Filter (rows=3590204.68)
            -> Hash Join (inner) (rows=3590204.68)
                -> Hash Join (inner) (rows=2556810.57)
                    -> Hash Join (inner) (rows=2477614.11)
                        -> Table "MOVIE_KEYWORD" as "MK" Full Scan (rows=4523930.00)
                        -> Record Buffer (record length: 33) (rows=1384676.93)
                            -> Filter (rows=1384676.93)
                                -> Table "TITLE" as "T" Full Scan (rows=2528312.00)
                    -> Record Buffer (record length: 25) (rows=2609129.00)
                        -> Table "MOVIE_COMPANIES" as "MC" Full Scan (rows=2609129.00)
                -> Record Buffer (record length: 33) (rows=3550187.76)
                    -> Filter (rows=3550187.76)
                        -> Table "MOVIE_INFO" as "MI" Access By ID (rows=3550187.76)
                            -> Bitmap
                                -> Index "INFO_TYPE_ID_MOVIE_INFO" Range Scan (full match)
```

---

## job_light_035

```sql
SELECT COUNT(*) FROM title t,movie_info mi,movie_info_idx mi_idx,movie_companies mc WHERE t.id=mi.movie_id AND t.id=mi_idx.movie_id AND t.id=mc.movie_id AND mi_idx.info_type_id=113 AND mi.info_type_id=105
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | 3.36 с | 0.10 с |
| отношение к бейслину | — | 0.03 |
| строк/чексумма | 1 / sha1:9a195fa80bdc9b5… | 1 / sha1:9a195fa80bdc9b5… (match) |
| fetches/reads | 1 620 651 | — |

**План бейслина (плоский):** `PLAN HASH (JOIN (MI INDEX (INFO_TYPE_ID_MOVIE_INFO), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES)), MI_IDX INDEX (INFO_TYPE_ID_MOVIE_INFO_IDX))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Filter
            -> Hash Join (inner)
                -> Nested Loop Join (inner)
                    -> Filter
                        -> Table "MOVIE_INFO" as "MI" Access By ID
                            -> Bitmap
                                -> Index "INFO_TYPE_ID_MOVIE_INFO" Range Scan (full match)
                    -> Filter
                        -> Table "TITLE" as "T" Access By ID
                            -> Bitmap
                                -> Index "TITLE_PK" Unique Scan
                    -> Filter
                        -> Table "MOVIE_COMPANIES" as "MC" Access By ID
                            -> Bitmap
                                -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
                -> Record Buffer (record length: 33)
                    -> Filter
                        -> Table "MOVIE_INFO_IDX" as "MI_IDX" Access By ID
                            -> Bitmap
                                -> Index "INFO_TYPE_ID_MOVIE_INFO_IDX" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN JOIN (MI_IDX INDEX (INFO_TYPE_ID_MOVIE_INFO_IDX), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES), MI INDEX (MOVIE_ID_MOVIE_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Nested Loop Join (inner) (rows=2.40)
            -> Filter (rows=1.00)
                -> Table "MOVIE_INFO_IDX" as "MI_IDX" Access By ID (rows=1.00)
                    -> Bitmap
                        -> Index "INFO_TYPE_ID_MOVIE_INFO_IDX" Range Scan (full match)
            -> Filter (rows=1.00)
                -> Table "TITLE" as "T" Access By ID (rows=1.00)
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter (rows=2.40)
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID (rows=2.40)
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
            -> Filter (rows=1.00)
                -> Table "MOVIE_INFO" as "MI" Access By ID (rows=5.99)
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_INFO" Range Scan (full match)
```

---

## job_light_023

```sql
SELECT COUNT(*) FROM cast_info ci,title t,movie_companies mc WHERE t.id=ci.movie_id AND t.id=mc.movie_id AND ci.role_id=2
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | 152.5 с | 12.49 с |
| отношение к бейслину | — | 0.08 |
| строк/чексумма | 1 / sha1:88980fcf3c1873f… | 1 / sha1:88980fcf3c1873f… (match) |
| fetches/reads | 84 720 599 | — |

**План бейслина (плоский):** `PLAN JOIN (CI INDEX (ROLE_ID_CAST_INFO), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Nested Loop Join (inner)
            -> Filter
                -> Table "CAST_INFO" as "CI" Access By ID
                    -> Bitmap
                        -> Index "ROLE_ID_CAST_INFO" Range Scan (full match)
            -> Filter
                -> Table "TITLE" as "T" Access By ID
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN HASH (HASH (MC NATURAL, T NATURAL), CI INDEX (ROLE_ID_CAST_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Filter (rows=7454395.68)
            -> Batch Hash Join (inner) (batches: 2) (rows=7454395.68)
                -> Record Buffer (record length: 50) (rows=2609129.00)
                    -> Hash Join (inner) (rows=2609129.00)
                        -> Table "MOVIE_COMPANIES" as "MC" Full Scan (rows=2609129.00)
                        -> Record Buffer (record length: 25) (rows=2528312.00)
                            -> Table "TITLE" as "T" Full Scan (rows=2528312.00)
                -> Record Buffer (record length: 33) (rows=7223497.98)
                    -> Filter (rows=7223497.98)
                        -> Table "CAST_INFO" as "CI" Access By ID (rows=7223497.98)
                            -> Bitmap
                                -> Index "ROLE_ID_CAST_INFO" Range Scan (full match)
```

---

## job_light_016

```sql
SELECT COUNT(*) FROM movie_keyword mk,title t,cast_info ci WHERE t.id=mk.movie_id AND t.id=ci.movie_id AND t.production_year>2014
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | 8.18 с | 0.87 с |
| отношение к бейслину | — | 0.11 |
| строк/чексумма | 1 / sha1:1fc014e4315768d… | 1 / sha1:1fc014e4315768d… (match) |
| fetches/reads | 23 162 306 | — |

**План бейслина (плоский):** `PLAN JOIN (MK NATURAL, T INDEX (TITLE_PK), CI INDEX (MOVIE_ID_CAST_INFO))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Nested Loop Join (inner)
            -> Table "MOVIE_KEYWORD" as "MK" Full Scan
            -> Filter
                -> Table "TITLE" as "T" Access By ID
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter
                -> Table "CAST_INFO" as "CI" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_CAST_INFO" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN JOIN (T NATURAL, MK INDEX (MOVIE_ID_MOVIE_KEYWORD), CI INDEX (MOVIE_ID_CAST_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Nested Loop Join (inner) (rows=292687.67)
            -> Filter (rows=10547.96)
                -> Table "TITLE" as "T" Full Scan (rows=2528312.00)
            -> Filter (rows=1.79)
                -> Table "MOVIE_KEYWORD" as "MK" Access By ID (rows=1.79)
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_KEYWORD" Range Scan (full match)
            -> Filter (rows=15.51)
                -> Table "CAST_INFO" as "CI" Access By ID (rows=15.51)
                    -> Bitmap
                        -> Index "MOVIE_ID_CAST_INFO" Range Scan (full match)
```

---

## job_light_024

```sql
SELECT COUNT(*) FROM cast_info ci,title t,movie_companies mc WHERE t.id=ci.movie_id AND t.id=mc.movie_id AND ci.role_id=4
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | 50.09 с | 5.84 с |
| отношение к бейслину | — | 0.12 |
| строк/чексумма | 1 / sha1:b0830d1fe9d0c47… | 1 / sha1:b0830d1fe9d0c47… (match) |
| fetches/reads | 30 230 071 | — |

**План бейслина (плоский):** `PLAN JOIN (CI INDEX (ROLE_ID_CAST_INFO), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Nested Loop Join (inner)
            -> Filter
                -> Table "CAST_INFO" as "CI" Access By ID
                    -> Bitmap
                        -> Index "ROLE_ID_CAST_INFO" Range Scan (full match)
            -> Filter
                -> Table "TITLE" as "T" Access By ID
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN HASH (HASH (MC NATURAL, T NATURAL), CI INDEX (ROLE_ID_CAST_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Filter (rows=2613214.99)
            -> Hash Join (inner) (rows=2613214.99)
                -> Hash Join (inner) (rows=2609129.00)
                    -> Table "MOVIE_COMPANIES" as "MC" Full Scan (rows=2609129.00)
                    -> Record Buffer (record length: 25) (rows=2528312.00)
                        -> Table "TITLE" as "T" Full Scan (rows=2528312.00)
                -> Record Buffer (record length: 33) (rows=2532271.43)
                    -> Filter (rows=2532271.43)
                        -> Table "CAST_INFO" as "CI" Access By ID (rows=2532271.43)
                            -> Bitmap
                                -> Index "ROLE_ID_CAST_INFO" Range Scan (full match)
```

---

## job_light_029

```sql
SELECT COUNT(*) FROM title t,cast_info ci,movie_companies mc WHERE t.id=mc.movie_id AND t.id=ci.movie_id AND t.production_year>2010 AND ci.role_id=1
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | 150.6 с | 18.62 с |
| отношение к бейслину | — | 0.12 |
| строк/чексумма | 1 / sha1:3f70b79025ed21b… | 1 / sha1:3f70b79025ed21b… (match) |
| fetches/reads | 84 563 069 | — |

**План бейслина (плоский):** `PLAN JOIN (CI INDEX (ROLE_ID_CAST_INFO), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Nested Loop Join (inner)
            -> Filter
                -> Table "CAST_INFO" as "CI" Access By ID
                    -> Bitmap
                        -> Index "ROLE_ID_CAST_INFO" Range Scan (full match)
            -> Filter
                -> Table "TITLE" as "T" Access By ID
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN JOIN (T NATURAL, MC INDEX (MOVIE_ID_MOVIE_COMPANIES), CI INDEX (MOVIE_ID_CAST_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Nested Loop Join (inner) (rows=2793677.38)
            -> Filter (rows=403962.27)
                -> Table "TITLE" as "T" Full Scan (rows=2528312.00)
            -> Filter (rows=1.13)
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID (rows=1.13)
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
            -> Filter (rows=6.12)
                -> Table "CAST_INFO" as "CI" Access By ID (rows=15.51)
                    -> Bitmap
                        -> Index "MOVIE_ID_CAST_INFO" Range Scan (full match)
```

---

## job_light_048

```sql
SELECT COUNT(*) FROM title t,movie_info mi,movie_companies mc,cast_info ci WHERE t.id=mi.movie_id AND t.id=mc.movie_id AND t.id=ci.movie_id AND ci.role_id=2 AND mi.info_type_id=16 AND t.production_year>2005 AND t.production_year<2009
```

| | бейслин 8e23f5f87eea | прогон 27.10 (f54cbf8fac) |
|---|---|---|
| время | 114.0 с | 18.59 с |
| отношение к бейслину | — | 0.16 |
| строк/чексумма | 1 / sha1:332ec8824e3bb56… | 1 / sha1:332ec8824e3bb56… (match) |
| fetches/reads | 367 709 066 | — |

**План бейслина (плоский):** `PLAN JOIN (MI INDEX (INFO_TYPE_ID_MOVIE_INFO), T INDEX (TITLE_PK), MC INDEX (MOVIE_ID_MOVIE_COMPANIES), CI INDEX (MOVIE_ID_CAST_INFO))`

**Детальный план бейслина:**
```
Select Expression
    -> Aggregate
        -> Nested Loop Join (inner)
            -> Filter
                -> Table "MOVIE_INFO" as "MI" Access By ID
                    -> Bitmap
                        -> Index "INFO_TYPE_ID_MOVIE_INFO" Range Scan (full match)
            -> Filter
                -> Table "TITLE" as "T" Access By ID
                    -> Bitmap
                        -> Index "TITLE_PK" Unique Scan
            -> Filter
                -> Table "MOVIE_COMPANIES" as "MC" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
            -> Filter
                -> Table "CAST_INFO" as "CI" Access By ID
                    -> Bitmap
                        -> Index "MOVIE_ID_CAST_INFO" Range Scan (full match)
```

**План прогона 27.10 (плоский):** `PLAN HASH (JOIN (T NATURAL, MC INDEX (MOVIE_ID_MOVIE_COMPANIES), MI INDEX (MOVIE_ID_MOVIE_INFO)), CI INDEX (ROLE_ID_CAST_INFO))`

**Детальный план прогона 27.10:**
```
Select Expression
    -> Aggregate (rows=1.00)
        -> Filter (rows=3809077.49)
            -> Batch Hash Join (inner) (batches: 2) (rows=3809077.49)
                -> Record Buffer (record length: 75) (rows=1333223.37)
                    -> Nested Loop Join (inner) (rows=1333223.37)
                        -> Filter (rows=857476.34)
                            -> Table "TITLE" as "T" Full Scan (rows=2528312.00)
                        -> Filter (rows=1.08)
                            -> Table "MOVIE_COMPANIES" as "MC" Access By ID (rows=1.08)
                                -> Bitmap
                                    -> Index "MOVIE_ID_MOVIE_COMPANIES" Range Scan (full match)
                        -> Filter (rows=1.43)
                            -> Table "MOVIE_INFO" as "MI" Access By ID (rows=5.99)
                                -> Bitmap
                                    -> Index "MOVIE_ID_MOVIE_INFO" Range Scan (full match)
                -> Record Buffer (record length: 33) (rows=7223497.98)
                    -> Filter (rows=7223497.98)
                        -> Table "CAST_INFO" as "CI" Access By ID (rows=7223497.98)
                            -> Bitmap
                                -> Index "ROLE_ID_CAST_INFO" Range Scan (full match)
```

---

