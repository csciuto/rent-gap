"""
Generate data.json from renters.parquet.
Adds "Married" (MARST 1-2) to partner dimension and "Any" to sex dimension.
"""
import pandas as pd, numpy as np, json

df = pd.read_parquet('/workspace/rentThing/renters.parquet')

# Partner label: married takes precedence over has_partner
df['partner_label'] = 'No partner'
df.loc[df['has_partner'] == 1, 'partner_label'] = 'Has partner'
df.loc[df['MARST'].isin([1, 2]), 'partner_label'] = 'Married'

df['inc_band'] = pd.cut(df['INCTOT'],
    bins=[0, 35000, 55000, 80000, 110000, 9_999_999],
    labels=['<$35k', '$35-55k', '$55-80k', '$80-110k', '$110k+'])

def get_frame(specs):
    frames = []
    for sfip, pumas in specs:
        mask = df['STATEFIP'] == int(sfip)
        if pumas:
            mask = mask & df['PUMA_str'].isin(pumas)
        frames.append(df[mask])
    return pd.concat(frames).drop_duplicates(subset=['SERIAL', 'PUMA_str'])

CITY_SPECS = {
    'Manhattan':     [('36',{'04103','04104','04107','04108','04109','04110','04111','04112','04121','04165'})],
    'Brooklyn':      [('36',{'04301','04302','04303','04304','04305','04306','04307','04308','04309','04310','04311','04312','04313','04314','04315','04316','04317','04318'})],
    'Queens':        [('36',{'04401','04402','04403','04404','04405','04406','04407','04408','04409','04410','04411','04412','04413','04414'})],
    'Bronx':         [('36',{'04204','04205','04207','04208','04209','04210','04211','04212','04221','04263'})],
    'Boston (city)': [('25',{'00801','00802','00803','00804','00805','00806'})],
    'San Francisco (city)': [('06',{'07507','07508','07509','07510','07511','07512','07513','07514'})],
    'Washington DC': [('11', None)],
    'Boston Metro':  [('25', None)],
    'SF Bay Area':   [('06',{
        '07507','07508','07509','07510','07511','07512','07513','07514',
        '00101','00111','00112','00113','00114','00115','00116','00117','00118','00119','00120','00121','00122','00123',
        '08101','08102','08103','08104','08105','08106',
        '08505','08506','08507','08508','08510','08511','08512','08515','08516','08517','08518','08519','08520','08521','08522',
    })],
    'NYC Metro':     [
        ('36', {'04103','04104','04107','04108','04109','04110','04111','04112','04121','04165',
                '04301','04302','04303','04304','04305','04306','04307','04308','04309','04310',
                '04311','04312','04313','04314','04315','04316','04317','04318',
                '04401','04402','04403','04404','04405','04406','04407','04408','04409','04410',
                '04411','04412','04413','04414',
                '04204','04205','04207','04208','04209','04210','04211','04212','04221','04263',
                *[p for p in df[df['STATEFIP']==36]['PUMA_str'].unique()
                  if p[:3] in ('009','012','028','033','031','032')]}),
        ('34', {p for p in df[df['STATEFIP']==34]['PUMA_str'].unique()
                if p[:3] in ('006','005','003','004')}),
    ],
    'DC Metro':      [
        ('11', None),
        ('24', {p for p in df[df['STATEFIP']==24]['PUMA_str'].unique()
                if p[:3] in ('008','010','011','013')}),
        ('51', {p for p in df[df['STATEFIP']==51]['PUMA_str'].unique()
                if p[:3] in ('013','014','015','510','076','054')}),
    ],
    'Los Angeles':   [('06',{'03703','03704','03705','03706','03707','03708','03709','03710','03711','03712','03713','03714','03715','03716','03717','03718','03719','03720','03721','03722','03723','03724','03725','03728','03730','03731','03732','03733','03734','03735','03736','03737','03738','03739','03740','03741','03742','03743','03744','03745','03746','03747','03748','03750','03751','03752','03753','03754','03757','03758','03759','03760','03761','03762','03763','03764','03766','03767','03768','03770','03771','03772','03773','03774','03775','03776','03778','03779','03780','03781','03782'})],
    'San Diego':     [('06',{'07301','07302','07303','07304','07305','07306','07307','07308','07309','07310','07311','07312','07313','07314','07315','07316','07317','07318','07319','07320','07321','07322','07323','07324','07325','07326','07327','07328','07329','07330','07331'})],
    'Seattle':       [('53',{'23301','23302','23303','23304','23305','23306','23307','23308','23309','23310','23311','23312','23313','23314','23315','23316','23317','23318'})],
    'Chicago':       [('17',{'03101','03102','03103','03104','03105','03106','03107','03108','03109','03110','03111','03112','03113','03114','03115','03116','03117','03118','03151','03152','03153','03154','03155','03156','03157','03158','03159','03160','03161','03162','03163','03164','03165','03166','03167','03168'})],
    'Miami-Dade':    [('12',{'08601','08602','08603','08604','08605','08606','08607','08608','08609','08610','08611','08612','08613','08614','08615','08616','08617','08618','08619','08620','08621','08622','08623','08624','08625'})],
    'Denver':        [('08',{'01701','01702','01703','01704','01705'})],
    'Atlanta':       [('13',{'01401','01402','01403','01404','01405','01406','01407','01408','01501','01502','01503','01504','01505','01506'})],
    'Houston':       [('48',{'04601','04602','04603','04604','04605','04606','04607','04608','04609','04610','04611','04612','04613','04614','04615','04616','04617','04618','04619','04620','04621','04622','04623','04624','04625','04626','04627','04628','04629','04630','04631','04633','04634','04635','04636','04637','04638','04639','04640'})],
    'Dallas':        [('48',{'02301','02302','02303','02304','02305','02306','02307','02308','02309','02310','02311','02312','02313','02314','02315','02316','02317','02318','02319','02320','02321','02322'})],
    'Phoenix':       [('04',{'00101','00102','00103','00104','00105','00106','00107','00108','00109','00110','00111','00112','00113','00114','00115','00116','00117','00118','00119','00120','00121','00122','00123','00124','00125','00126','00127','00128','00129','00130','00131','00132','00133','00134','00135'})],
    'Portland OR':   [('41',{'05101','05102','05103','05104','05105','05106','05107','05108','05109','05110','05111','05112','05113','05114','05115','05116','05117','05118'})],
    'Austin':        [('48',{'01800','01901','01902','01903','01904','01905','01907','01908','01909'})],
}

EDUC_F = {
    'All':              lambda d: d,
    'BA+ Liberal Arts': lambda d: d[(d['EDUC'] >= 10) & (d['degfield'] == 'Liberal Arts')],
    'BA+ STEM':         lambda d: d[(d['EDUC'] >= 10) & (d['degfield'] == 'STEM')],
    'BA+ Business':     lambda d: d[(d['EDUC'] >= 10) & (d['degfield'] == 'Business')],
    'BA+ (any)':        lambda d: d[d['EDUC'] >= 10],
    'No college':       lambda d: d[d['EDUC'] <= 6],
}
RACE_F = {
    'All races': lambda d: d,
    'White':     lambda d: d[d['raceth'] == 'White'],
    'Black':     lambda d: d[d['raceth'] == 'Black'],
    'Hispanic':  lambda d: d[d['raceth'] == 'Hispanic'],
    'Asian':     lambda d: d[d['raceth'] == 'Asian'],
}
CHILD_F = {
    'Any':       lambda d: d,
    'Childless': lambda d: d[d['has_child'] == 0],
    'Has child': lambda d: d[d['has_child'] == 1],
}
# NEW: "Married" added, "Any" now includes married people
PARTNER_F = {
    'Any':         lambda d: d,
    'No partner':  lambda d: d[d['partner_label'] == 'No partner'],
    'Has partner': lambda d: d[d['partner_label'] == 'Has partner'],
    'Married':     lambda d: d[d['partner_label'] == 'Married'],
}
# NEW: "Any" sex option
SEX_F = {
    'Women': lambda d: d[d['sex_label'] == 'Women'],
    'Men':   lambda d: d[d['sex_label'] == 'Men'],
    'Any':   lambda d: d,
}

MIN_WPOP, MIN_ROWS = 50, 10

def wmedian(v, w):
    idx = np.argsort(v); sv, sw = v[idx], w[idx]; cs = np.cumsum(sw)
    return float(sv[cs >= cs[-1] / 2][0])

def w_ci95(v, w):
    W = w.sum(); n_eff = W**2 / (w**2).sum()
    mu = np.average(v, weights=w); sd = np.sqrt(np.average((v - mu)**2, weights=w))
    return round(float(1.96 * 1.2533 * sd / np.sqrt(max(n_eff, 1))), 1)

def cell_from(g):
    w  = g['PERWT'].values.astype(float)
    rv = g['RENTGRS'].values.astype(float)
    pv = g['per_rent'].values.astype(float)
    hv = g['N_HH'].values.astype(float)
    bv = g['burden'].values.astype(float)
    sev = (g['burden'] >= 50).values.astype(float)
    W = w.sum(); n_eff = W**2 / (w**2).sum()
    mu_h = np.average(hv, weights=w)
    ci_h = round(float(1.96 * np.sqrt(np.average((hv - mu_h)**2, weights=w) / max(n_eff, 1))), 3)
    sev_p = float(np.average(sev, weights=w))
    return {
        'u':    int(wmedian(rv, w)),   'ci_u': int(w_ci95(rv, w)),
        'p':    int(wmedian(pv, w)),   'ci_p': int(w_ci95(pv, w)),
        'h':    round(float(mu_h), 2), 'ci_h': ci_h,
        'b':    round(float(wmedian(bv, w)), 1), 'ci_b': round(w_ci95(bv, w), 1),
        's':    round(sev_p * 100, 1),
        'ci_s': round(float(1.96 * np.sqrt(max(sev_p * (1 - sev_p) / max(n_eff, 1), 0))) * 100, 1),
        'n':    int(W), 'r': len(g),
    }

def build_cube(frame):
    out = {}
    for sx, sf in SEX_F.items():
        for rx, rf in RACE_F.items():
            for ex, ef in EDUC_F.items():
                for cx, cf in CHILD_F.items():
                    for px, pf in PARTNER_F.items():
                        sub = pf(cf(ef(rf(sf(frame)))))
                        if len(sub) < MIN_ROWS: continue
                        key = f"{sx}|{rx}|{ex}|{cx}|{px}"
                        by_inc = {}
                        for inc, g in sub.groupby('inc_band', observed=True):
                            if len(g) < MIN_ROWS or g['PERWT'].sum() < MIN_WPOP: continue
                            by_inc[str(inc)] = cell_from(g)
                        if len(sub) >= MIN_ROWS and sub['PERWT'].sum() >= MIN_WPOP:
                            by_inc['All'] = cell_from(sub)
                        if by_inc:
                            out[key] = by_inc
    return out

def build_meta(frame):
    out = {}
    for sx, sf in SEX_F.items():
        for rx, rf in RACE_F.items():
            for ex, ef in EDUC_F.items():
                for cx, cf in CHILD_F.items():
                    for px, pf in PARTNER_F.items():
                        sub = pf(cf(ef(rf(sf(frame)))))
                        if len(sub) < MIN_ROWS: continue
                        W = sub['PERWT'].sum()
                        if W < MIN_WPOP: continue
                        key = f"{sx}|{rx}|{ex}|{cx}|{px}"
                        out[key] = {
                            'mi': int(wmedian(sub['INCTOT'].values, sub['PERWT'].values)),
                            'n':  int(W),
                            'r':  len(sub),
                        }
    return out

print("Building data cubes...")
cities_data, meta_data = {}, {}

all_frames = [get_frame(specs) for specs in CITY_SPECS.values()]
all_frame  = pd.concat(all_frames).drop_duplicates(subset=['SERIAL', 'PUMA_str'])
print(f"  All metros: {len(all_frame):,} rows")
cities_data['All metros'] = build_cube(all_frame)
meta_data['All metros']   = build_meta(all_frame)
print(f"  All metros: {len(cities_data['All metros'])} group keys")

for city, specs in CITY_SPECS.items():
    cdf = get_frame(specs)
    cities_data[city] = build_cube(cdf)
    meta_data[city]   = build_meta(cdf)
    print(f"  {city}: {len(cdf):,} rows → {len(cities_data[city])} keys")

payload = {
    'cities': cities_data,
    'meta':   meta_data,
    'inc':    ['<$35k', '$35-55k', '$55-80k', '$80-110k', '$110k+'],
}
raw = json.dumps(payload, separators=(',', ':'))
open('/workspace/rentThing/data.json', 'w').write(raw)
print(f"\ndata.json: {len(raw)/1024/1024:.1f} MB, {len(cities_data)} cities")
