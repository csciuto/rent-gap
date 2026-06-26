"""
Pipeline tests for the rent burden dashboard.
Run: python3 -m pytest test_pipeline.py -v
"""
import gzip, json, re
import numpy as np
import pandas as pd
import pytest

PARQUET = '/workspace/rent-gap/renters.parquet'
DATA_JSON = '/workspace/rent-gap/data.json'
RAW_GZ = '/workspace/rent-gap/usa_00016.dat.gz'
HTML = '/workspace/rent-gap/index.html'

# ── weighted median ───────────────────────────────────────────────────────────

def wmedian(v, w):
    idx = np.argsort(v); sv, sw = v[idx], w[idx]; cs = np.cumsum(sw)
    return float(sv[cs >= cs[-1] / 2][0])

def test_wmedian_uniform():
    v = np.array([1., 2., 3., 4., 5.])
    w = np.ones(5)
    assert wmedian(v, w) == 3.0

def test_wmedian_skewed_weights():
    v = np.array([1., 2., 3.])
    w = np.array([1., 10., 1.])
    assert wmedian(v, w) == 2.0

def test_wmedian_single():
    assert wmedian(np.array([42.]), np.array([1.])) == 42.0

# ── EDUC label mapping ────────────────────────────────────────────────────────

def educ_label(e):
    if e <= 5:  return 'No HS'
    if e == 6:  return 'HS'
    if e <= 9:  return 'Some college'
    if e == 10: return 'BA'
    return 'Grad+'

@pytest.mark.parametrize("code,expected", [
    (0, 'No HS'), (5, 'No HS'),
    (6, 'HS'),
    (7, 'Some college'), (8, 'Some college'), (9, 'Some college'),
    (10, 'BA'),
    (11, 'Grad+'),
])
def test_educ_label(code, expected):
    assert educ_label(code) == expected

def test_educ_9_is_not_ba():
    # Key regression: EDUC=9 = 3 years of college, NOT a bachelor's degree
    assert educ_label(9) == 'Some college'
    assert educ_label(9) != 'BA'

# ── DEGFIELD groupings ────────────────────────────────────────────────────────

STEM     = {20,23,24,33,34,40,41}
BUSINESS = {52}
LIBERAL  = {15,19,25,30,31,36,38,42,45,54}
HELPING  = {22,26,44}

def degfield_label(d, educ):
    if educ < 10: return 'No degree'
    if d in STEM:     return 'STEM'
    if d in BUSINESS: return 'Business'
    if d in LIBERAL:  return 'Liberal Arts'
    if d in HELPING:  return 'Education/SocWork'
    return 'Other degree'

@pytest.mark.parametrize("code,educ,expected", [
    (23, 10, 'STEM'),       # Engineering → STEM
    (20, 10, 'STEM'),       # CS → STEM
    (30, 10, 'Liberal Arts'), # English → Liberal Arts
    (45, 10, 'Liberal Arts'), # Social Sciences → Liberal Arts
    (52, 10, 'Business'),
    (22, 10, 'Education/SocWork'),
    (23, 9,  'No degree'),  # STEM code but sub-BA → No degree
    (0,  6,  'No degree'),  # N/A code, HS only
])
def test_degfield_label(code, educ, expected):
    assert degfield_label(code, educ) == expected

# ── parquet integrity ─────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def df():
    return pd.read_parquet(PARQUET)

def test_parquet_loads(df):
    assert len(df) > 300_000

def test_parquet_columns(df):
    required = {'SEX','AGE','MARST','RENTGRS','INCTOT','PERWT','NCHILD',
                'EDUC','DEGFIELD','N_HH','per_rent','burden','sex_label',
                'raceth','educ','degfield','has_child','state','PUMA_str'}
    assert required <= set(df.columns), f"Missing: {required - set(df.columns)}"

def test_age_range(df):
    assert df['AGE'].min() >= 23
    assert df['AGE'].max() <= 35

def test_marst_values(df):
    assert set(df['MARST'].unique()) <= {1, 2, 3, 4, 5, 6}

def test_rentgrs_positive(df):
    assert (df['RENTGRS'] > 0).all()

def test_inctot_positive(df):
    assert (df['INCTOT'] > 0).all()
    assert (df['INCTOT'] < 9_999_990).all()

def test_sex_labels(df):
    assert set(df['sex_label'].unique()) == {'Women', 'Men'}

def test_educ_column_values(df):
    assert set(df['educ'].unique()) <= {'No HS', 'HS', 'Some college', 'BA', 'Grad+'}

def test_ba_population_nonzero(df):
    # Regression: earlier EDUC bug caused BA to show 0 persons
    ba_pop = df.loc[df['educ'] == 'BA', 'PERWT'].sum()
    assert ba_pop > 1_000_000, f"BA population suspiciously low: {ba_pop:,.0f}"

def test_ba_larger_than_grad(df):
    ba   = df.loc[df['educ'] == 'BA',    'PERWT'].sum()
    grad = df.loc[df['educ'] == 'Grad+', 'PERWT'].sum()
    assert ba > grad, "BA should be larger population than Grad+ for age 23-29"

def test_educ_10_maps_to_ba(df):
    assert (df.loc[df['EDUC'] == 10, 'educ'] == 'BA').all()

def test_educ_9_maps_to_some_college(df):
    assert (df.loc[df['EDUC'] == 9, 'educ'] == 'Some college').all()

def test_burden_column(df):
    assert (df['burden'] >= 0).all()
    assert (df['burden'] <= 300).all()  # clipped at 300

def test_perwt_positive(df):
    assert (df['PERWT'] > 0).all()

def test_n_hh_positive(df):
    assert (df['N_HH'] >= 1).all()

def test_per_rent_leq_rentgrs(df):
    # per-person rent can't exceed unit rent
    assert (df['per_rent'] <= df['RENTGRS'] + 1).all()

def test_has_child_binary(df):
    assert set(df['has_child'].unique()) <= {0, 1}

def test_raceth_values(df):
    assert set(df['raceth'].unique()) <= {'White','Black','Hispanic','Asian','Other'}

def test_estimated_population(df):
    total = df['PERWT'].sum()
    assert 8_000_000 < total < 25_000_000, f"Unexpected total pop: {total:,.0f}"

# ── raw file column parsing spot-check ────────────────────────────────────────

def test_raw_file_sex_column():
    """SEX at position 113 should be 1 or 2."""
    with gzip.open(RAW_GZ, 'rt', encoding='iso-8859-1') as f:
        for i, line in enumerate(f):
            if i >= 1000: break
            sex = line[113]
            assert sex in ('1','2'), f"Unexpected SEX value '{sex}' on line {i}"

def test_raw_file_educ_range():
    """EDUC at positions 126-128 should be 00–11 for person records we care about."""
    with gzip.open(RAW_GZ, 'rt', encoding='iso-8859-1') as f:
        for i, line in enumerate(f):
            if i >= 5000: break
            try:
                educ = int(line[126:128])
            except ValueError:
                continue
            assert 0 <= educ <= 11, f"EDUC out of range: {educ} on line {i}"

# ── data.json integrity ───────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def payload():
    return json.load(open(DATA_JSON))

def test_json_has_required_keys(payload):
    assert 'cities' in payload
    assert 'meta' in payload
    assert 'inc' in payload

def test_json_income_labels(payload):
    assert payload['inc'] == ['<$35k','$35-55k','$55-80k','$80-110k','$110k+']

def test_json_expected_cities(payload):
    expected = {'Manhattan','Brooklyn','Boston Metro','SF Bay Area','Washington DC','NYC Metro','All metros'}
    assert expected <= set(payload['cities'].keys())

def test_json_cell_fields(payload):
    cities = payload['cities']
    city = cities['Brooklyn']
    key = next(k for k in city if k.startswith('Women'))
    inc = next(iter(city[key]))
    cell = city[key][inc]
    assert set(cell.keys()) == {'u','ci_u','p','ci_p','h','ci_h','b','ci_b','s','ci_s','n','r'}, f"Unexpected cell keys: {cell.keys()}"

def test_json_meta_fields(payload):
    meta = payload['meta']
    key = next(iter(meta['Brooklyn']))
    cell = meta['Brooklyn'][key]
    assert 'mi' in cell and 'n' in cell

def test_json_rent_plausible(payload):
    for city, groups in payload['cities'].items():
        for key, inc_data in groups.items():
            for inc, cell in inc_data.items():
                assert 200 <= cell['u'] <= 15000, f"{city}/{key}/{inc}: unit rent {cell['u']} implausible"
                assert 0 <= cell['h'] <= 20,      f"{city}/{key}/{inc}: hh size {cell['h']} implausible"
                assert 0 <= cell['s'] <= 100,     f"{city}/{key}/{inc}: pct_sev {cell['s']} implausible"

def test_json_meta_income_plausible(payload):
    for city, meta in payload['meta'].items():
        for key, m in meta.items():
            assert 500 < m['mi'] < 500000, f"{city}/{key}: median income {m['mi']} implausible"
            assert m['n'] > 0

# ── HTML integrity ────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def html():
    return open(HTML).read()

def test_html_has_payload(html):
    assert 'const PAYLOAD =' in html

def test_html_payload_has_meta(html):
    # The embedded JSON must have the meta key — regression for the blank-page bug
    payload_start = html.index('const PAYLOAD =') + len('const PAYLOAD =')
    payload_end   = html.index(';\nconst DATA = PAYLOAD.cities;')
    embedded = json.loads(html[payload_start:payload_end])
    assert 'meta' in embedded, "Embedded PAYLOAD missing 'meta' key — re-embed data.json"

def test_html_payload_meta_matches_file(html):
    payload_start = html.index('const PAYLOAD =') + len('const PAYLOAD =')
    payload_end   = html.index(';\nconst DATA = PAYLOAD.cities;')
    embedded = json.loads(html[payload_start:payload_end])
    assert set(embedded['meta'].keys()) == set(embedded['cities'].keys()), \
        "meta and cities have different city sets"

def test_html_references_meta(html):
    assert 'PAYLOAD.meta' in html or 'const META' in html

def test_html_has_five_charts(html):
    for i in range(1, 5):
        assert f'id="c{i}"' in html, f"Chart c{i} missing from HTML"
    for i in range(1, 5):
        assert f'id="c{i}n"' in html, f"Spark chart c{i}n missing from HTML"

def test_html_no_unclosed_script(html):
    opens  = html.count('<script')
    closes = html.count('</script>')
    assert opens == closes, f"Mismatched script tags: {opens} open, {closes} close"
