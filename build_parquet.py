"""
Rebuild renters.parquet from usa_00016.dat.gz.
Two-pass approach: first pass computes N_HH and has_partner per household,
second pass extracts target persons.
Now includes MARST=1,2 (married people) for comparison with unmarried.
"""
import gzip, pandas as pd, numpy as np
from collections import defaultdict

COLS = {
    'SERIAL':   (14, 22),
    'STATEFIP': (61, 63),
    'PUMA':     (63, 68),
    'GQ':       (80, 81),
    'RENTGRS':  (85, 90),
    'PERWT':    (96, 106),
    'NCHILD':   (106, 107),
    'SEX':      (113, 114),
    'AGE':      (114, 117),
    'MARST':    (117, 118),
    'RACE':     (118, 119),
    'HISPAN':   (122, 123),
    'EDUC':     (126, 128),
    'DEGFIELD': (131, 133),
    'INCTOT':   (141, 148),
}

STATE_NAMES = {
    1:'AL',2:'AK',4:'AZ',5:'AR',6:'CA',8:'CO',9:'CT',10:'DE',11:'DC',12:'FL',
    13:'GA',15:'HI',16:'ID',17:'IL',18:'IN',19:'IA',20:'KS',21:'KY',22:'LA',
    23:'ME',24:'MD',25:'MA',26:'MI',27:'MN',28:'MS',29:'MO',30:'MT',31:'NE',
    32:'NV',33:'NH',34:'NJ',35:'NM',36:'NY',37:'NC',38:'ND',39:'OH',40:'OK',
    41:'OR',42:'PA',44:'RI',45:'SC',46:'SD',47:'TN',48:'TX',49:'UT',50:'VT',
    51:'VA',53:'WA',54:'WV',55:'WI',56:'WY',
}

STEM     = {20,23,24,33,34,40,41}
BUSINESS = {52}
LIBERAL  = {15,19,25,30,31,36,38,42,45,54}
HELPING  = {22,26,44}

def educ_label(e):
    if e <= 5:  return 'No HS'
    if e == 6:  return 'HS'
    if e <= 9:  return 'Some college'
    if e == 10: return 'BA'
    return 'Grad+'

def degfield_label(d, educ_int):
    if educ_int < 10: return 'No degree'
    if d in STEM:     return 'STEM'
    if d in BUSINESS: return 'Business'
    if d in LIBERAL:  return 'Liberal Arts'
    if d in HELPING:  return 'Education/SocWork'
    return 'Other degree'

print("Pass 1: computing household sizes and detecting unmarried partners...")
hh_size        = defaultdict(int)  # SERIAL → total persons in renter household
partner_serials = set()            # SERIALs with RELATE=11 (unmarried partner)
rental_serials  = set()            # SERIALs that are rental units

with gzip.open('/workspace/rentThing/usa_00016.dat.gz', 'rt', encoding='iso-8859-1') as f:
    for line in f:
        line = line.rstrip('\n')
        if line[80] not in ('1','2','5'): continue
        try:
            serial  = int(line[14:22])
            rentgrs = int(line[85:90])
            relate  = int(line[107:109])
        except:
            continue
        hh_size[serial] += 1
        if rentgrs > 0:
            rental_serials.add(serial)
        if relate == 11:
            partner_serials.add(serial)

print(f"  {len(rental_serials):,} rental households found")
print(f"  {len(partner_serials):,} households with unmarried partners")

print("\nPass 2: extracting target persons (age 23-35, all marital statuses)...")
records, buf = [], []
CHUNK = 300_000

with gzip.open('/workspace/rentThing/usa_00016.dat.gz', 'rt', encoding='iso-8859-1') as f:
    for line in f:
        line = line.rstrip('\n')
        if line[80] not in ('1','2','5'): continue
        try:
            serial = int(line[14:22])
        except:
            continue
        if serial not in rental_serials: continue
        try:
            age    = int(line[114:117])
        except:
            continue
        if age < 23 or age > 35: continue
        try:
            rentgrs = int(line[85:90])
        except:
            continue
        if rentgrs <= 0: continue
        try:
            inctot = int(line[141:148])
        except:
            continue
        if inctot <= 0 or inctot >= 9_999_990: continue
        row = {}
        for k, (s, e) in COLS.items():
            try:
                row[k] = int(line[s:e])
            except:
                row[k] = None
        records.append(row)
        if len(records) >= CHUNK:
            buf.append(pd.DataFrame(records))
            records = []
            print(f"  {sum(len(b) for b in buf):,} rows so far...")
    if records:
        buf.append(pd.DataFrame(records))

df = pd.concat(buf, ignore_index=True)
print(f"  {len(df):,} total person-records extracted")

for c in df.columns:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df['PERWT'] /= 100
df = df[(df['INCTOT'] > 0) & (df['INCTOT'] < 9_999_990)].copy()

# Household-level attributes
df['N_HH']       = df['SERIAL'].map(hh_size).fillna(1).astype(int)
df['has_partner'] = df['SERIAL'].isin(partner_serials).astype(int)

# Derived columns
df['state']     = df['STATEFIP'].map(STATE_NAMES)
df['PUMA_str']  = df['PUMA'].apply(lambda x: str(int(x)).zfill(5) if pd.notna(x) else '')
df['per_rent']  = df['RENTGRS'] / df['N_HH']
df['burden']    = (df['RENTGRS'] * 12 / df['INCTOT'] * 100).clip(upper=300)
df['sex_label'] = df['SEX'].map({1:'Men', 2:'Women'})
df['has_child'] = (df['NCHILD'] > 0).astype(int)

def raceth(row):
    if row['HISPAN'] >= 1: return 'Hispanic'
    r = row['RACE']
    if r == 1: return 'White'
    if r == 2: return 'Black'
    if r in (4,5,6): return 'Asian'
    return 'Other'
df['raceth']   = df.apply(raceth, axis=1)
df['educ']     = df['EDUC'].apply(educ_label)
df['degfield'] = df.apply(lambda r: degfield_label(int(r['DEGFIELD']), int(r['EDUC'])), axis=1)

print(f"\nMARST distribution:")
print(df['MARST'].value_counts().sort_index())
print(f"\nSex distribution:")
print(df.groupby('sex_label')['PERWT'].sum().apply(lambda x: f'{x:,.0f}'))
print(f"\nTotal: {len(df):,} rows, ~{int(df['PERWT'].sum()):,} est. persons")

cols = ['SERIAL','STATEFIP','PUMA','GQ','RENTGRS','PERWT','NCHILD','SEX','AGE','MARST',
        'RACE','HISPAN','EDUC','DEGFIELD','INCTOT','state','PUMA_str','burden','sex_label',
        'raceth','educ','degfield','has_child','N_HH','per_rent','has_partner']
df[cols].to_parquet('/workspace/rentThing/renters.parquet', index=False)
print("\nSaved renters.parquet")
