# rent-gap

Interactive dashboard for exploring rent burden among renters age 23–35 across 24 U.S. cities. Open `docs/index.html` in a browser.

---

## Data

**Source:** [IPUMS USA](https://usa.ipums.org/usa/) — ACS 2020–2024 5-year sample

**Universe:** Renters age 23–35, all marital statuses, gross rent > $0, personal income > $0

**Geography:** 24 cities and metro areas defined by 2020 PUMA codes, including individual NYC boroughs, full metro areas (NYC, SF Bay, Boston, DC), and 12 other major cities.

**Metrics per cell:**
- Median gross rent (full unit, incl. utilities)
- Median rent per person (unit ÷ household size)
- % severely rent-burdened (rent > 50% of income)
- Median household size

All medians are weighted (PERWT) with 95% confidence intervals via Kish effective sample size.

---

## Dashboard

`index.html` is self-contained — aggregated data is embedded. No server required, but for CORS-safe local serving:

```
python3 -m http.server 8080
```

**Dimensions:** City · Sex · Race/ethnicity · Education · Degree field · Children · Partner status

**X-axis:** Income band (<$35k · $35–55k · $55–80k · $80–110k · $110k+)

Up to 5 series can be plotted simultaneously. URL state is preserved for sharing.

---

## Reproducing

Requires an IPUMS USA ACS 2020–2024 5-year extract with variables:

`SERIAL STATEFIP PUMA GQ RENTGRS PERWT NCHILD RELATE SEX AGE MARST RACE HISPAN EDUC DEGFIELD INCTOT`

```bash
python3 build_parquet.py   # raw extract → renters.parquet (~21 MB)
python3 build_data.py      # renters.parquet → data.json (~12 MB)
python3 -m pytest test_pipeline.py  # 54 tests
```

Then re-embed `data.json` into `index.html`:

```python
html  = open('docs/index.html').read()
data  = open('data.json').read()
start = html.index('const PAYLOAD =') + len('const PAYLOAD =')
end   = html.index(';\nconst DATA = PAYLOAD.cities;')
open('docs/index.html','w').write(html[:start] + data + html[end:])
```

---

## License

MIT — see [LICENSE](LICENSE). IPUMS microdata not included; aggregated statistics in `data.json` and `index.html` are freely redistributable per [IPUMS Terms of Use](https://ipums.org/about/terms).
