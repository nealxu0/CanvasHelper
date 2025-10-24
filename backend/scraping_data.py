# backend/scraping_data.py
"""
Robust downloader + feature engineering for OULAD (Open University Learning Analytics)
- Downloads dataset via kagglehub
- Locates relevant CSVs (assessments, studentAssessment, studentVle*, vle, studentInfo)
- Normalizes column names
- Engineers features per student-assessment:
    - weight, assessment_type, score
    - vle_count_prior (sum of clicks for student)
    - past_avg_score (student's mean score across assessments)
- Creates a proxy target 'assignment_hours' grounded in real signals
- Saves backend/training_data/oulad_training.csv
"""

import os
from pathlib import Path
import zipfile
import pandas as pd
import numpy as np
import kagglehub

OUT_DIR = Path("backend/training_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

KAGGLE_DATASET_ID = "vjcalling/ouladdata"  # OULAD copy; change if you prefer another id

def find_csvs(root: Path):
    """Return list of all csv files under root (non-recursive and recursive)."""
    files = []
    try:
        for p in root.rglob("*.csv"):
            files.append(str(p))
    except Exception:
        # fallback: list root directly
        for p in root.iterdir():
            if p.is_file() and p.name.lower().endswith(".csv"):
                files.append(str(p))
    return sorted(files)

def pick_file(csv_list, keywords_include=None, keywords_exclude=None):
    """
    Pick best matching file from csv_list based on include/exclude keywords (case-insensitive).
    Returns None if no match.
    """
    if not csv_list:
        return None
    include = [k.lower() for k in (keywords_include or [])]
    exclude = [k.lower() for k in (keywords_exclude or [])]

    # exact filename priority
    for p in csv_list:
        name = Path(p).name.lower()
        if any(name == inc + ".csv" for inc in include):
            return p

    # otherwise pick first that contains any include and none of exclude
    for p in csv_list:
        name = Path(p).name.lower()
        if include and not any(inc in name for inc in include):
            continue
        if exclude and any(ex in name for ex in exclude):
            continue
        return p

    # last fallback, return first csv
    return csv_list[0]

print("Downloading Kaggle dataset:", KAGGLE_DATASET_ID)
dataset_path = kagglehub.dataset_download(KAGGLE_DATASET_ID)
print("Downloaded dataset to:", dataset_path)

# If dataset_path contains zip(s) extract them to a tmp directory under OUT_DIR
path_obj = Path(dataset_path)
csv_files = find_csvs(path_obj)

# If nothing found directly (kagglehub sometimes puts files in nested dir or zip), search for zips and extract
if not csv_files:
    zips = list(path_obj.rglob("*.zip"))
    if zips:
        tmp = OUT_DIR / "oulad_extracted"
        tmp.mkdir(exist_ok=True)
        for z in zips:
            try:
                with zipfile.ZipFile(z, "r") as zf:
                    zf.extractall(tmp)
            except Exception as e:
                print(f"Warning: failed to extract {z}: {e}")
        csv_files = find_csvs(tmp)
        data_root = tmp
    else:
        data_root = path_obj
else:
    data_root = path_obj

csv_files = find_csvs(Path(data_root))
print("Found CSV files:", csv_files)

# Pick the right files robustly
assessments_fp = pick_file(csv_files, keywords_include=["assessments"], keywords_exclude=["student"])
student_assess_fp = pick_file(csv_files, keywords_include=["studentassessment", "student_assessment", "student-assessment"], keywords_exclude=[])
# studentVLE: there may be many files like studentVle_0.csv ... studentVle_7.csv -> collect all
student_vle_list = [p for p in csv_files if "studentvle" in Path(p).name.lower() or "student_vle" in Path(p).name.lower()]
vle_fp = pick_file(csv_files, keywords_include=["vle"], keywords_exclude=["studentvle"])
student_info_fp = pick_file(csv_files, keywords_include=["studentinfo", "student_info"], keywords_exclude=[])

print("Files chosen:")
print(" - assessments:", assessments_fp)
print(" - studentAssessment:", student_assess_fp)
print(" - studentVle files:", student_vle_list[:10])
print(" - vle (meta):", vle_fp)
print(" - studentInfo:", student_info_fp)

def safe_read_csv(path, **kwargs):
    try:
        return pd.read_csv(path, low_memory=False, **kwargs)
    except Exception as e:
        print(f"Warning: failed to read {path}: {e}")
        return None

# Load files
assessments = safe_read_csv(assessments_fp) if assessments_fp else None
student_assess = safe_read_csv(student_assess_fp) if student_assess_fp else None

# load & concat studentVle parts if multiple
student_vle = None
if student_vle_list:
    parts = []
    for p in student_vle_list:
        dfp = safe_read_csv(p)
        if dfp is not None:
            parts.append(dfp)
    if parts:
        student_vle = pd.concat(parts, ignore_index=True)

vle = safe_read_csv(vle_fp) if vle_fp else None
student_info = safe_read_csv(student_info_fp) if student_info_fp else None

# If core tables missing, save a fallback and exit gracefully
if assessments is None or student_assess is None:
    print("ERROR: required core tables (assessments / studentAssessment) are missing.")
    # Save any CSV as fallback for inspection
    if csv_files:
        fallback_path = Path(csv_files[0])
        try:
            df_fallback = pd.read_csv(fallback_path, low_memory=False)
            df_fallback.to_csv(OUT_DIR / "oulad_raw_fallback.csv", index=False)
            print("Saved raw fallback CSV at", OUT_DIR / "oulad_raw_fallback.csv")
        except Exception:
            pass
    raise SystemExit("Missing required OULAD core tables. Inspect downloaded dataset.")

# Normalize column names
def normalize(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

assessments = normalize(assessments)
student_assess = normalize(student_assess)
if student_vle is not None:
    student_vle = normalize(student_vle)
if vle is not None:
    vle = normalize(vle)
if student_info is not None:
    student_info = normalize(student_info)

print("assessments columns:", assessments.columns.tolist())
print("student_assess columns:", student_assess.columns.tolist())
if student_vle is not None:
    print("sample student_vle columns:", student_vle.columns.tolist()[:20])

# Ensure consistent key names: id_assessment and id_student
# For assessments: prefer 'id_assessment' as key; if not present look for 'id' or 'assessment_id'
if 'id_assessment' not in assessments.columns:
    if 'id' in assessments.columns:
        assessments = assessments.rename(columns={'id': 'id_assessment'})
    elif 'assessment_id' in assessments.columns:
        assessments = assessments.rename(columns={'assessment_id': 'id_assessment'})

if 'id_assessment' not in student_assess.columns:
    if 'id' in student_assess.columns:
        student_assess = student_assess.rename(columns={'id': 'id_assessment'})

# Some copies use studentid vs id_student
if 'id_student' not in student_assess.columns:
    if 'studentid' in student_assess.columns:
        student_assess = student_assess.rename(columns={'studentid': 'id_student'})
    elif 'student_id' in student_assess.columns:
        student_assess = student_assess.rename(columns={'student_id': 'id_student'})

if 'id_student' not in assessments.columns:
    if 'studentid' in assessments.columns:
        assessments = assessments.rename(columns={'studentid': 'id_student'})

# For assessments file ensure weight column exists (may be weight or assessment_weight)
if 'weight' not in assessments.columns:
    if 'assessment_weight' in assessments.columns:
        assessments = assessments.rename(columns={'assessment_weight': 'weight'})

# Merge studentAssessment with assessments metadata
# student_assess typically has columns: id_assessment, id_student, date_submitted, is_banked, score
# assessments typically has columns: id_assessment, code_module, code_presentation, assessment_type, date, weight
merged = student_assess.merge(
    assessments,
    on='id_assessment',
    how='left',
    suffixes=('_stu', '_assess')
)

print("Merged shape:", merged.shape)
print("Merged sample columns:", merged.columns.tolist()[:30])

# Compute VLE clicks per student (vle_count)
vle_count_df = None
if student_vle is not None:
    # preferred click column names
    click_col = None
    for c in ['sum_click', 'sumclick', 'clicks', 'sum_click', 'activity', 'count']:
        if c in student_vle.columns:
            click_col = c
            break
    if click_col is None:
        # fallback: count rows per student
        student_vle['_vle_row_count'] = 1
        click_col = '_vle_row_count'

    # ensure id_student exists in student_vle
    if 'id_student' not in student_vle.columns:
        if 'studentid' in student_vle.columns:
            student_vle = student_vle.rename(columns={'studentid':'id_student'})

    # aggregate clicks by student
    try:
        vle_count_df = student_vle.groupby('id_student')[click_col].sum().reset_index().rename(columns={click_col: 'vle_clicks_total'})
    except Exception as e:
        print("Warning: failed to aggregate student_vle clicks:", e)
        vle_count_df = None

# Past average score per student (from student_assess)
past_avg = student_assess.groupby('id_student').agg(past_avg_score=('score', 'mean')).reset_index()
past_avg['past_avg_score'] = past_avg['past_avg_score'].fillna(0)

# Merge aggregates into merged table
merged = merged.merge(past_avg, left_on='id_student', right_on='id_student', how='left')
if vle_count_df is not None:
    merged = merged.merge(vle_count_df, left_on='id_student', right_on='id_student', how='left')
    merged['vle_clicks_total'] = merged['vle_clicks_total'].fillna(0)
else:
    merged['vle_clicks_total'] = 0

# Ensure weight exists
merged['weight'] = merged.get('weight', np.nan)

# Build feature rows
rows = []
for _, r in merged.iterrows():
    sid = r.get('id_student')
    aid = r.get('id_assessment')
    assess_type = r.get('assessment_type') or r.get('type') or None
    weight = r.get('weight') if pd.notna(r.get('weight')) else 0.0
    score = r.get('score') if pd.notna(r.get('score')) else np.nan
    vle_count = r.get('vle_clicks_total') if pd.notna(r.get('vle_clicks_total')) else 0.0
    past = r.get('past_avg_score') if pd.notna(r.get('past_avg_score')) else np.nan

    rows.append({
        'student_id': sid,
        'assessment_id': aid,
        'assessment_type': assess_type,
        'weight': float(weight),
        'score': float(score) if not pd.isna(score) else np.nan,
        'vle_count_total': float(vle_count),
        'past_avg_score': float(past) if not pd.isna(past) else np.nan
    })

df_feat = pd.DataFrame(rows)

# Compute proxy target assignment_hours
def compute_hours_proxy(row, alpha=0.06, beta=0.35, gamma=0.025, base=0.75):
    """
    Proxy formula:
      hours = base + (weight * alpha) + log1p(vle_count_total) * beta - (past_avg_score_norm * gamma * 10)
    Purpose: heavier-weight assessments + more VLE activity -> more time; higher past score -> less time.
    Coefficients tuned to produce reasonable ranges (0.25 to ~12 hours).
    """
    w = row.get('weight') or 0.0
    vlec = row.get('vle_count_total') or 0.0
    past = row.get('past_avg_score') if not pd.isna(row.get('past_avg_score')) else 50.0
    try:
        past_norm = float(past) / 100.0
    except Exception:
        past_norm = 0.5
    hours = base + (w * alpha) + np.log1p(vlec) * beta - (past_norm * gamma * 10.0)
    hours = max(0.25, float(hours))
    hours = min(hours, 20.0)
    return round(hours, 2)

df_feat['assignment_hours'] = df_feat.apply(compute_hours_proxy, axis=1)

# Final cleanup
df_final = df_feat.dropna(subset=['student_id', 'assessment_id']).reset_index(drop=True)

out_path = OUT_DIR / "oulad_training.csv"
df_final.to_csv(out_path, index=False)
print(f"Saved engineered training data with proxy target at: {out_path}")
print("Sample rows:")
print(df_final.head(10).to_string(index=False))
