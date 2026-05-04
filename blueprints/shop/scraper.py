"""
Scraper pour racquetfinder.com — extrait les données des raquettes de tennis.
Corrections :
  - head_size : parse "95 sq. in." → float
  - poids : convertit ounces → grammes (1 oz = 28.3495 g)
"""
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://www.racquetfinder.com'
OZ_TO_G = 28.3495

KNOWN_BRANDS = [
    'Wilson', 'Head', 'Babolat', 'Yonex', 'Prince', 'Tecnifibre',
    'Dunlop', 'Volkl', 'Solinco', 'ProKennex', 'Pacific', 'Gamma',
    'Lacoste', 'Boris Becker', 'Donnay', 'Asics', 'Adidas', 'Mizuno',
    'One Strings', 'PowerAngle',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


# ── Parseurs de champs ──────────────────────────────────────────────────────

def extract_brand_and_name(full_name: str):
    """Extraire la marque et le nom depuis le nom complet."""
    for brand in KNOWN_BRANDS:
        if full_name.lower().startswith(brand.lower() + ' '):
            return brand, full_name[len(brand):].strip()
    return 'Unknown', full_name


def _parse_string_pattern(raw: str) -> str | None:
    """Convertit '16 Mains/19 Crosses' → '16x19'."""
    if not raw:
        return None
    m = re.search(r'(\d+)\s*[Mm]ains?\s*/?\s*(\d+)', raw)
    if m:
        return f'{m.group(1)}x{m.group(2)}'
    return raw.strip() or None


def _parse_head_size(raw: str) -> float | None:
    """Extrait la taille du tamis en sq. in. depuis '95 sq. in.' ou '95 sq. in. / 613 sq. cm.'"""
    if not raw:
        return None
    m = re.search(r'([\d.]+)\s*sq\.?\s*in', raw, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _parse_weight_oz_to_g(raw: str) -> float | None:
    """Parse '11.5 oz' et convertit en grammes (arrondi à 1 décimale)."""
    if not raw:
        return None
    m = re.search(r'([\d.]+)\s*oz', raw, re.IGNORECASE)
    if m:
        return round(float(m.group(1)) * OZ_TO_G, 1)
    # Parfois affiché directement en grammes
    m = re.search(r'([\d.]+)\s*g\b', raw, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _parse_length(raw: str) -> float | None:
    """Extrait la longueur en pouces depuis '27.00 inches / 68.58 cm'."""
    if not raw:
        return None
    m = re.search(r'([\d.]+)\s*inch', raw, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _parse_balance(raw: str) -> float | None:
    """Parse la balance depuis '-6 pts HL' ou '+2 pts HH'."""
    if not raw:
        return None
    m = re.search(r'(-?\d+(?:\.\d+)?)\s*pts?\s*(HL|HH)', raw, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        if m.group(2).upper() == 'HL':
            return -abs(val)
        return abs(val)
    # Format numérique simple
    m = re.search(r'(-?\d+(?:\.\d+)?)', raw)
    if m:
        return float(m.group(1))
    return None


def _parse_table(soup_context) -> dict:
    """Parse toutes les lignes <tr><th>…</th><td>…</td></tr> en dict."""
    result = {}
    for row in soup_context.select('tr'):
        th = row.find('th')
        td = row.find('td')
        if th and td:
            key = th.get_text(strip=True).rstrip(':').strip()
            result[key] = td.get_text(strip=True)
    return result


# ── API du scraper ──────────────────────────────────────────────────────────

def parse_product(product_div) -> dict:
    """Parse un div.product de la page listing racquetfinder."""
    name_tag = product_div.select_one('.rac_name')
    full_name = name_tag.get_text(strip=True) if name_tag else ''

    # pcode depuis le lien /compare?x=1&pcode=XXX
    pcode = ''
    link = product_div.select_one('a[href*="pcode="]')
    if link:
        m = re.search(r'pcode=([A-Za-z0-9]+)', link.get('href', ''))
        if m:
            pcode = m.group(1).upper()

    table_data = _parse_table(product_div)

    # Marque priorité au champ Manufacturer
    if 'Manufacturer' in table_data:
        brand = table_data['Manufacturer']
        name = full_name[len(brand):].strip() if full_name.lower().startswith(brand.lower()) else full_name
    else:
        brand, name = extract_brand_and_name(full_name)

    # head_size depuis le tableau listing
    head_size = _parse_head_size(table_data.get('Head Size', ''))

    # string_pattern
    string_pattern = _parse_string_pattern(table_data.get('String Pattern', ''))

    # image
    img = product_div.select_one('img.rac_img, img[class*="rac"]')
    image_url = img.get('src', '') if img else ''

    return {
        'brand': brand,
        'name': name,
        'pcode': pcode,
        'head_size': head_size,
        'string_pattern': string_pattern,
        'image_url': image_url,
        'raw': table_data,
    }


def scrape_racquet_by_pcode(pcode: str) -> dict:
    """Scrape la page détail d'une raquette sur racquetfinder.com."""
    url = f'{BASE_URL}/racquet/{pcode.upper()}'
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return {}

    soup = BeautifulSoup(resp.text, 'lxml')

    h2 = soup.find('h2')
    full_name = h2.get_text(strip=True) if h2 else ''
    brand, name = extract_brand_and_name(full_name)

    img = soup.select_one('img.racimage')
    image_url = img.get('src', '') if img else ''

    # Table principale (div.with_image ou div.with_image.cf)
    container = soup.select_one('div.with_image')
    table_data = _parse_table(container) if container else _parse_table(soup)

    head_size = _parse_head_size(table_data.get('Head Size', ''))
    length = _parse_length(table_data.get('Length', ''))
    string_pattern = _parse_string_pattern(table_data.get('String Pattern', ''))
    strung_weight = _parse_weight_oz_to_g(
        table_data.get('Strung Weight') or table_data.get('Weight', '')
    )
    unstrung_weight = _parse_weight_oz_to_g(table_data.get('Unstrung Weight', ''))
    balance = _parse_balance(table_data.get('Balance', ''))
    swingweight_raw = table_data.get('Swingweight', '') or table_data.get('Swing Weight', '')
    swingweight = int(re.search(r'\d+', swingweight_raw).group()) if re.search(r'\d+', swingweight_raw) else None
    stiffness_raw = table_data.get('Stiffness', '') or table_data.get('Flex', '')
    stiffness = int(re.search(r'\d+', stiffness_raw).group()) if re.search(r'\d+', stiffness_raw) else None

    return {
        'pcode': pcode.upper(),
        'brand': brand,
        'name': name,
        'image_url': image_url,
        'head_size': head_size,
        'length': length,
        'string_pattern': string_pattern,
        'strung_weight': strung_weight,
        'unstrung_weight': unstrung_weight,
        'balance': balance,
        'swingweight': swingweight,
        'stiffness': stiffness,
        'raw': table_data,
    }


def fetch_manufacturers() -> list:
    """Récupère la liste des fabricants disponibles."""
    resp = requests.get(BASE_URL + '/', headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.text, 'lxml')
    select = soup.select_one('#manufacturer')
    if not select:
        return []
    result = []
    for opt in select.find_all('option'):
        val = opt.get('value', '').strip()
        if not val:
            continue
        label = opt.get_text(strip=True)
        result.append({'value': val, 'label': label})
    return result


def _build_params(manufacturer='', current_only=False, stiffness_min=None, stiffness_max=None, **kwargs) -> dict:
    params = {'manufacturer': manufacturer}
    if current_only:
        params['current'] = 'Y'
        params['currentcheckbox'] = 'ASICS'
    if stiffness_min is not None:
        params['fMin'] = str(stiffness_min)
    if stiffness_max is not None:
        params['fMax'] = str(stiffness_max)
    return params


def _stiffness_ranges() -> list:
    """Retourne les plages de rigidité pour paginer les résultats."""
    return [
        (0, 9),
        (10, 19),
        (20, 29),
        (30, 39),
        (40, 49),
        (50, 59),
        (60, 69),
        (70, 79),
        (80, 90),
    ]


def _fetch_products(params) -> list:
    """Appel HTTP et extraction des div.product."""
    resp = requests.get(BASE_URL + '/', params=params, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, 'lxml')
    return soup.select('div.product')


def _collect_products_partitioned(manufacturer='', current_only=False, stiffness_min=0, stiffness_max=9) -> list:
    """Collecte les produits pour une plage de rigidité."""
    params = _build_params(
        manufacturer=manufacturer, current_only=current_only,
        stiffness_min=stiffness_min, stiffness_max=stiffness_max
    )
    return _fetch_products(params)


def _collect_products_by_stiffness(manufacturer='', current_only=False) -> list:
    """Collecte tous les produits (dédupliqués) en parcourant les plages de rigidité."""
    seen_names = set()
    all_products = []

    for s_min, s_max in _stiffness_ranges():
        for p in _collect_products_partitioned(
            manufacturer=manufacturer, current_only=current_only,
            stiffness_min=s_min, stiffness_max=s_max
        ):
            name_tag = p.select_one('.rac_name')
            name = name_tag.get_text(strip=True) if name_tag else str(p)
            if name not in seen_names:
                seen_names.add(name)
                all_products.append(p)

    # Fallback sans filtre de rigidité (rattrape les omissions)
    for p in _fetch_products(_build_params(manufacturer=manufacturer, current_only=current_only)):
        name_tag = p.select_one('.rac_name')
        name = name_tag.get_text(strip=True) if name_tag else str(p)
        if name not in seen_names:
            seen_names.add(name)
            all_products.append(p)

    return all_products


def scrape_all(current_only=False, progress_callback=None) -> list[dict]:
    """
    Point d'entrée principal : scrape toutes les raquettes par fabricant.
    Retourne une liste de dict prêts à être insérés en base.
    """
    manufacturers = fetch_manufacturers()
    results = []

    for i, mfr in enumerate(manufacturers):
        if progress_callback:
            progress_callback(i, len(manufacturers), mfr['label'])
        products = _collect_products_by_stiffness(
            manufacturer=mfr['value'], current_only=current_only
        )
        for product_div in products:
            data = parse_product(product_div)
            results.append(data)

    return results


